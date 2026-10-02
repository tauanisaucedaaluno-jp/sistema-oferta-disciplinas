import csv
import io
from collections import defaultdict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import (
    Curso,
    VinculoCurricular,
    ConceitoDisciplina,
    CodigoDisciplina,
    Usuario,
    Historico,
    PeriodoLetivo,
    DemandaSnapshot,
)
from api.auth import obter_usuario_atual
from api.deps import registrar_acesso

from core.groups import (
    grupo_a,
    grupo_b,
    grupo_c,
    _formatos_periodo,
    _obter_nome_normalizado,
    _obter_codigos_disciplina,
    inicializar_context_cache,
    obter_periodo_cursando_referencia,
)

router = APIRouter()


def _obter_codigo_disciplina(db: Session, curso_codigo: str, conceito_id: str) -> str:
    """Busca o código oficial vigente da disciplina no PPC (ex.: AL0362)."""
    cods = (
        db.query(CodigoDisciplina)
        .filter(
            CodigoDisciplina.curso_codigo == curso_codigo,
            CodigoDisciplina.conceito_id == conceito_id,
        )
        .all()
    )
    if not cods:
        return conceito_id

    def prioridade(r):
        sit_score = 2 if r.situacao_curriculo == "CORRENTE" else (1 if r.situacao_curriculo in ("ATIVO", "ATIVA") else 0)
        versao = r.versao_ppc_origem or 0
        return (sit_score, versao)

    cod_escolhido = max(cods, key=prioridade)
    return cod_escolhido.codigo


def _mapear_codigos_disciplina(db: Session, curso_codigo: str = None) -> dict:
    """Retorna um mapeamento (curso_codigo, conceito_id) -> codigo_oficial."""
    query = db.query(CodigoDisciplina)
    if curso_codigo and curso_codigo != "TODOS":
        query = query.filter(CodigoDisciplina.curso_codigo == curso_codigo)

    registros = query.all()

    def prioridade(r):
        sit_score = 2 if r.situacao_curriculo == "CORRENTE" else (1 if r.situacao_curriculo in ("ATIVO", "ATIVA") else 0)
        versao = r.versao_ppc_origem or 0
        return (sit_score, versao)

    mapa = {}
    for r in sorted(registros, key=prioridade):
        mapa[(r.curso_codigo, r.conceito_id)] = r.codigo
    return mapa


@router.get("/cursos")
def listar_cursos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """Retorna a lista de todos os cursos que possuem alunos cadastrados."""
    from db.models import Aluno
    cursos_com_alunos = set(r[0] for r in db.query(Aluno.curso_codigo).distinct().all())
    cursos = db.query(Curso).filter(Curso.codigo.in_(cursos_com_alunos)).order_by(Curso.nome).all()
    if not cursos:
        cursos = db.query(Curso).order_by(Curso.nome).all()
    return [{"codigo": c.codigo, "nome": c.nome} for c in cursos]


class CriarPeriodoRequest(BaseModel):
    periodo: str
    descricao: str = ""
    is_atual: bool = False


@router.get("/periodos")
def listar_periodos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Retorna a lista dinâmica de períodos letivos de planejamento cadastrados no banco de dados para o coordenador atual.
    Cada usuário possui sua própria visão isolada de períodos. Se não tiver nenhum semestre cadastrado ainda, retorna lista vazia.
    """
    import re

    # 1. Busca exclusivamente períodos cadastrados por este usuário
    periodos_db = db.query(PeriodoLetivo).filter(PeriodoLetivo.usuario_id == usuario_atual.id).all()
    if not periodos_db:
        return []

    # Garante que pelo menos um período válido seja marcado como atual
    if not any(p.is_atual for p in periodos_db):
        periodos_db[0].is_atual = True
        db.commit()

    periodos_cadastrados = {p.codigo: p for p in periodos_db}

    # 2. Busca contagens por período no Histórico (apenas para os períodos cadastrados deste usuário)
    formatos_alvo = []
    for cod in periodos_cadastrados.keys():
        formatos_alvo.extend(_formatos_periodo(cod))

    stats = (
        db.query(
            Historico.periodo_letivo,
            func.count(Historico.id),
            func.sum(case((Historico.situacao == "cursando", 1), else_=0)),
        )
        .filter(Historico.periodo_letivo.in_(formatos_alvo))
        .group_by(Historico.periodo_letivo)
        .all()
    )
    stats_map = {r[0]: (r[1], int(r[2] or 0)) for r in stats}

    def parse_periodo(p_str: str):
        match = re.match(r"^(\d{4})[./\-]0?([12])$", p_str.strip())
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)

    codigos_validos = list(periodos_cadastrados.keys())
    codigos_validos.sort(key=parse_periodo, reverse=True)

    resultado = []
    for c in codigos_validos:
        tot, curs = stats_map.get(c, (0, 0))
        if tot == 0:
            for fmt in _formatos_periodo(c):
                if fmt in stats_map:
                    t_f, c_f = stats_map[fmt]
                    tot += t_f
                    curs += c_f

        ano, sem = parse_periodo(c)
        p_obj = periodos_cadastrados.get(c)
        is_atual = p_obj.is_atual if p_obj else False

        resultado.append({
            "codigo": c,
            "ano": ano,
            "semestre": sem,
            "tipo": "impar" if sem == 1 else "par",
            "descricao": p_obj.descricao if (p_obj and p_obj.descricao) else f"{ano}/{sem}",
            "total_registros": tot,
            "total_cursando": curs,
            "is_atual": is_atual,
        })

    return resultado


@router.post("/periodos")
def criar_periodo(
    req: CriarPeriodoRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Cria ou habilita oficialmente um novo semestre letivo para o sistema (ex.: '2026/2').
    Isolado por coordenador logado.
    """
    import re
    p_clean = req.periodo.strip()
    match = re.match(r"^(\d{4})[./\-]0?([12])$", p_clean)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use o padrão AAAA/1 ou AAAA/2.",
        )
    ano = int(match.group(1))
    semestre = int(match.group(2))
    codigo_canonico = f"{ano}/{semestre}"

    if req.is_atual:
        db.query(PeriodoLetivo).filter(
            PeriodoLetivo.usuario_id == usuario_atual.id,
            PeriodoLetivo.is_atual == True,
        ).update({"is_atual": False})

    existente = db.query(PeriodoLetivo).filter(
        PeriodoLetivo.usuario_id == usuario_atual.id,
        PeriodoLetivo.codigo == codigo_canonico,
    ).first()
    if existente:
        existente.descricao = req.descricao or existente.descricao
        existente.is_atual = req.is_atual
    else:
        novo = PeriodoLetivo(
            usuario_id=usuario_atual.id,
            codigo=codigo_canonico,
            ano=ano,
            semestre=semestre,
            descricao=req.descricao or f"{ano}/{semestre}",
            is_atual=req.is_atual,
        )
        db.add(novo)
        db.flush()

        # Garante que o novo semestre nasça 100% zerado e isolado de semestres anteriores (ex.: 2026/1)
        vinculos = db.query(VinculoCurricular.curso_codigo, VinculoCurricular.conceito_id).distinct().all()
        snapshots_zerados = [
            DemandaSnapshot(
                usuario_id=usuario_atual.id,
                periodo_codigo=codigo_canonico,
                curso_codigo=c_cod,
                conceito_id=conc_id,
                grupo_a_qtd=0,
                grupo_b_qtd=0,
                grupo_c_qtd=0,
                grupo_a_prob=0.0,
                grupo_c_prob=0.0,
                demanda_estimada=0.0,
            )
            for c_cod, conc_id in vinculos
        ]
        if snapshots_zerados:
            db.bulk_save_objects(snapshots_zerados)

    db.commit()

    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(
        db,
        "criacao_periodo_letivo",
        f"Período: {codigo_canonico}, Descrição: {req.descricao}, Atual: {req.is_atual}",
        usr_id,
    )

    return {
        "status": "sucesso",
        "codigo": codigo_canonico,
        "ano": ano,
        "semestre": semestre,
        "mensagem": f"Semestre {codigo_canonico} cadastrado com sucesso.",
    }


@router.delete("/periodos/{periodo:path}")
def excluir_periodo(
    periodo: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Exclui um semestre letivo e os snapshots de demanda associados a ele para o coordenador atual.
    Permite à coordenação remover uploads errados, períodos de teste ou resíduos.
    """
    p_clean = periodo.strip().replace("-", "/")
    formatos = _formatos_periodo(p_clean)

    # 1. Deleta registros de Historico do período
    linhas_historico = db.query(Historico).filter(Historico.periodo_letivo.in_(formatos)).delete(synchronize_session=False)

    # 2. Deleta snapshots de demanda do período e deste usuário
    db.query(DemandaSnapshot).filter(
        DemandaSnapshot.usuario_id == usuario_atual.id,
        DemandaSnapshot.periodo_codigo.in_(formatos),
    ).delete(synchronize_session=False)

    # 3. Deleta registro de PeriodoLetivo deste usuário
    db.query(PeriodoLetivo).filter(
        PeriodoLetivo.usuario_id == usuario_atual.id,
        PeriodoLetivo.codigo.in_(formatos),
    ).delete(synchronize_session=False)

    db.commit()

    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(
        db,
        "exclusao_periodo_letivo",
        f"Período: {p_clean}, Linhas de histórico removidas: {linhas_historico}",
        usr_id,
    )

    return {
        "status": "sucesso",
        "periodo": p_clean,
        "linhas_removidas": linhas_historico,
        "mensagem": f"Semestre {p_clean} excluído com sucesso do seu painel ({linhas_historico} registros removidos).",
    }


def _tem_dados_academicos(db: Session, context_cache: dict = None) -> bool:
    """Verifica se existem registros de histórico escolar carregados no banco de dados."""
    if context_cache is not None:
        if "tem_dados_historico" in context_cache:
            return context_cache["tem_dados_historico"]
    existe = db.query(Historico.id).first() is not None
    if context_cache is not None:
        context_cache["tem_dados_historico"] = existe
    return existe


def _periodo_possui_dados(db: Session, periodo_atual: str, context_cache: dict = None) -> bool:
    """Verifica se existem registros em Historico para o período solicitado."""
    if context_cache is not None:
        if "tem_dados_periodo" in context_cache:
            return context_cache["tem_dados_periodo"]
    
    formatos = _formatos_periodo(periodo_atual)
    existe = db.query(Historico.id).filter(Historico.periodo_letivo.in_(formatos)).first() is not None
    if context_cache is not None:
        context_cache["tem_dados_periodo"] = existe
    return existe


def _calcular_demanda_por_vinculo(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str, context_cache: dict = None) -> dict:
    """Calcula A, B, C e demanda estimada para um par (curso, conceito)."""
    # Se o banco de dados não possui nenhum registro acadêmico importado OU se o período não possui matrículas importadas:
    if not _tem_dados_academicos(db, context_cache) or not _periodo_possui_dados(db, periodo_atual, context_cache):
        return {
            "curso_codigo": curso_codigo,
            "grupo_a_qtd": 0,
            "grupo_a_prob": 0.0,
            "grupo_b_qtd": 0,
            "grupo_c_qtd": 0,
            "grupo_c_prob": 0.0,
            "demanda_estimada": 0.0,
            "total_alunos": 0,
        }

    periodo_cursando = obter_periodo_cursando_referencia(db, periodo_atual, curso_codigo, context_cache)
    ga = grupo_a(db, curso_codigo, conceito_id, periodo_cursando, context_cache)
    gb = grupo_b(db, curso_codigo, conceito_id, context_cache)
    gc = grupo_c(db, curso_codigo, conceito_id, periodo_cursando, context_cache)
    prob_a = sum(aluno.probabilidade_reprovacao for aluno in ga)
    prob_c = sum(aluno.probabilidade_aprovacao for aluno in gc)
    total_ponderado = prob_a + len(gb) + prob_c
    return {
        "curso_codigo": curso_codigo,
        "grupo_a_qtd": len(ga),
        "grupo_a_prob": round(prob_a, 2),
        "grupo_b_qtd": len(gb),
        "grupo_c_qtd": len(gc),
        "grupo_c_prob": round(prob_c, 2),
        # RF11 / RN08: soma ponderada (Σ prob reprovação A + |B| + Σ prob aprovação C)
        "demanda_estimada": round(total_ponderado, 2),
        # Contagem inteira de alunos distintos (A + B + C sem ponderação)
        "total_alunos": len(ga) + len(gb) + len(gc),
    }


def _obter_demandas_por_snapshot(db: Session, curso_codigo: str, periodo_atual: str, usuario_id: Optional[int] = None):
    """
    Tenta carregar o resultado consolidado diretamente de DemandaSnapshot.
    Garante que cálculos de períodos antigos permaneçam imutáveis e isolados por usuário.
    """
    mapa_codigos = _mapear_codigos_disciplina(db, curso_codigo if curso_codigo != "TODOS" else None)

    if curso_codigo != "TODOS":
        filtros = [
            DemandaSnapshot.periodo_codigo == periodo_atual,
            DemandaSnapshot.curso_codigo == curso_codigo,
        ]
        if usuario_id is not None:
            filtros.append(DemandaSnapshot.usuario_id == usuario_id)

        snaps = (
            db.query(DemandaSnapshot, VinculoCurricular, ConceitoDisciplina)
            .outerjoin(
                VinculoCurricular,
                (DemandaSnapshot.curso_codigo == VinculoCurricular.curso_codigo)
                & (DemandaSnapshot.conceito_id == VinculoCurricular.conceito_id),
            )
            .outerjoin(ConceitoDisciplina, DemandaSnapshot.conceito_id == ConceitoDisciplina.id)
            .filter(*filtros)
            .all()
        )
        if not snaps:
            return None

        resultado = []
        for snap, vinc, conc in snaps:
            cod_oficial = mapa_codigos.get((curso_codigo, snap.conceito_id), snap.conceito_id)
            dados_curso = {
                "curso_codigo": curso_codigo,
                "disciplina_codigo": cod_oficial,
                "grupo_a_qtd": snap.grupo_a_qtd,
                "grupo_a_prob": snap.grupo_a_prob,
                "grupo_b_qtd": snap.grupo_b_qtd,
                "grupo_c_qtd": snap.grupo_c_qtd,
                "grupo_c_prob": snap.grupo_c_prob,
                "demanda_estimada": snap.demanda_estimada,
                "total_alunos": snap.grupo_a_qtd + snap.grupo_b_qtd + snap.grupo_c_qtd,
            }
            nome_disc = conc.nome_normalizado if conc else snap.conceito_id
            p_sug = vinc.periodo_sugerido if vinc else None
            p_oferta = vinc.periodicidade_oferta if vinc else None
            resultado.append({
                "conceito_id": snap.conceito_id,
                "disciplina_codigo": cod_oficial,
                "disciplina_nome": nome_disc,
                "periodo_sugerido": p_sug,
                "periodicidade_oferta": p_oferta,
                "grupo_a_qtd": snap.grupo_a_qtd,
                "grupo_b_qtd": snap.grupo_b_qtd,
                "grupo_c_qtd": snap.grupo_c_qtd,
                "demanda_estimada": snap.demanda_estimada,
                "total_alunos": snap.grupo_a_qtd + snap.grupo_b_qtd + snap.grupo_c_qtd,
                "demanda_por_curso": [dados_curso],
            })
        return resultado
    else:
        # TODOS os cursos
        filtros = [DemandaSnapshot.periodo_codigo == periodo_atual]
        if usuario_id is not None:
            filtros.append(DemandaSnapshot.usuario_id == usuario_id)

        snaps = (
            db.query(DemandaSnapshot, VinculoCurricular, ConceitoDisciplina)
            .outerjoin(
                VinculoCurricular,
                (DemandaSnapshot.curso_codigo == VinculoCurricular.curso_codigo)
                & (DemandaSnapshot.conceito_id == VinculoCurricular.conceito_id),
            )
            .outerjoin(ConceitoDisciplina, DemandaSnapshot.conceito_id == ConceitoDisciplina.id)
            .filter(*filtros)
            .all()
        )
        if not snaps:
            return None

        grupos_por_nome = defaultdict(list)
        for snap, vinc, conc in snaps:
            nome_chave = conc.nome_normalizado if conc else snap.conceito_id
            grupos_por_nome[nome_chave].append((snap, vinc, conc))

        resultado = []
        for nome_normalizado, itens in sorted(grupos_por_nome.items()):
            demanda_por_curso = []
            total_a_qtd = 0
            total_a_prob = 0.0
            total_b = 0
            total_c_qtd = 0
            total_c_prob = 0.0
            total_alunos = 0

            snap_ref, vinc_ref, conc_ref = itens[0]
            periodo_sugerido = vinc_ref.periodo_sugerido if len(itens) == 1 else None
            periodicidade_oferta = vinc_ref.periodicidade_oferta if len(itens) == 1 else "ambos"

            for snap, vinc, conc in itens:
                cod_oficial = mapa_codigos.get((vinc.curso_codigo, vinc.conceito_id), vinc.conceito_id)
                demanda_por_curso.append({
                    "curso_codigo": vinc.curso_codigo,
                    "disciplina_codigo": cod_oficial,
                    "grupo_a_qtd": snap.grupo_a_qtd,
                    "grupo_a_prob": snap.grupo_a_prob,
                    "grupo_b_qtd": snap.grupo_b_qtd,
                    "grupo_c_qtd": snap.grupo_c_qtd,
                    "grupo_c_prob": snap.grupo_c_prob,
                    "demanda_estimada": snap.demanda_estimada,
                    "total_alunos": snap.grupo_a_qtd + snap.grupo_b_qtd + snap.grupo_c_qtd,
                })
                total_a_qtd += snap.grupo_a_qtd
                total_a_prob += snap.grupo_a_prob
                total_b += snap.grupo_b_qtd
                total_c_qtd += snap.grupo_c_qtd
                total_c_prob += snap.grupo_c_prob
                total_alunos += (snap.grupo_a_qtd + snap.grupo_b_qtd + snap.grupo_c_qtd)

            demanda_total = round(total_a_prob + total_b + total_c_prob, 2)
            cod_ref = mapa_codigos.get((vinc_ref.curso_codigo, conc_ref.id), conc_ref.id)

            resultado.append({
                "conceito_id": conc_ref.id,
                "disciplina_codigo": cod_ref,
                "disciplina_nome": nome_normalizado,
                "periodo_sugerido": periodo_sugerido,
                "periodicidade_oferta": periodicidade_oferta,
                "grupo_a_qtd": total_a_qtd,
                "grupo_b_qtd": total_b,
                "grupo_c_qtd": total_c_qtd,
                "demanda_estimada": demanda_total,
                "total_alunos": total_alunos,
                "demanda_por_curso": demanda_por_curso,
            })
        return resultado


@router.get("")
def obter_demandas(
    curso_codigo: str,
    periodo_atual: str,
    modo: str = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Retorna o cálculo de demanda de todas as disciplinas vinculadas ao curso no período.

    Prioriza o snapshot imutável salvo em DemandaSnapshot para garantir isolamento total
    entre semestres diferentes (ex.: 2026/1 vs 2027/1) e entre usuários.
    """
    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(db, "consulta_demanda", f"Curso: {curso_codigo}, Periodo: {periodo_atual}", usr_id)

    # 1. Verifica se existe snapshot salvo para este período e usuário
    dados_snapshot = _obter_demandas_por_snapshot(db, curso_codigo, periodo_atual, usuario_id=usr_id)
    if dados_snapshot is not None:
        return dados_snapshot

    if curso_codigo == "TODOS":
        return _obter_demandas_todos_cursos(db, periodo_atual)

    # --- Consulta por curso específico ---
    vinculos_query = (
        db.query(VinculoCurricular)
        .join(ConceitoDisciplina, VinculoCurricular.conceito_id == ConceitoDisciplina.id)
        .filter(VinculoCurricular.curso_codigo == curso_codigo)
        .all()
    )

    if not vinculos_query:
        return []

    vinculos = list(vinculos_query)
    mapa_codigos = _mapear_codigos_disciplina(db, curso_codigo)

    context_cache = inicializar_context_cache(db, curso_codigo)
    resultado = []
    for vinc in vinculos:
        conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == vinc.conceito_id).first()
        if not conceito:
            continue

        dados_curso = _calcular_demanda_por_vinculo(db, curso_codigo, vinc.conceito_id, periodo_atual, context_cache)
        cod_oficial = mapa_codigos.get((curso_codigo, vinc.conceito_id), vinc.conceito_id)
        dados_curso["disciplina_codigo"] = cod_oficial

        resultado.append({
            "conceito_id": vinc.conceito_id,
            "disciplina_codigo": cod_oficial,
            "disciplina_nome": conceito.nome_normalizado,
            "periodo_sugerido": vinc.periodo_sugerido,
            "periodicidade_oferta": vinc.periodicidade_oferta,
            "grupo_a_qtd": dados_curso["grupo_a_qtd"],
            "grupo_b_qtd": dados_curso["grupo_b_qtd"],
            "grupo_c_qtd": dados_curso["grupo_c_qtd"],
            "demanda_estimada": dados_curso["demanda_estimada"],
            "total_alunos": dados_curso["total_alunos"],
            # RF12 — quebra por curso (para curso único, lista com 1 item)
            "demanda_por_curso": [dados_curso],
        })

    return resultado


def _obter_demandas_todos_cursos(db: Session, periodo_atual: str):
    """
    RF12 — Consolida demanda de todos os cursos, agrupando disciplinas
    pelo nome_normalizado (mesma disciplina em cursos diferentes).
    """
    from db.models import Aluno
    cursos_com_alunos = set(r[0] for r in db.query(Aluno.curso_codigo).distinct().all())

    # Busca vínculos apenas dos cursos que possuem alunos matriculados
    todos_vinculos = (
        db.query(VinculoCurricular, ConceitoDisciplina)
        .join(ConceitoDisciplina, VinculoCurricular.conceito_id == ConceitoDisciplina.id)
        .filter(VinculoCurricular.curso_codigo.in_(cursos_com_alunos))
        .all()
    )

    mapa_codigos = _mapear_codigos_disciplina(db)

    # Agrupa por nome_normalizado (disciplinas "iguais" em cursos diferentes)
    # Estrutura: {nome_normalizado: [(vinculo, conceito), ...]}
    grupos_por_nome: dict = defaultdict(list)
    for vinc, conceito in todos_vinculos:
        grupos_por_nome[conceito.nome_normalizado].append((vinc, conceito))

    context_cache = inicializar_context_cache(db, None)
    resultado = []
    for nome_normalizado, pares in sorted(grupos_por_nome.items()):
        demanda_por_curso = []
        total_a_qtd = 0
        total_a_prob = 0.0
        total_b = 0
        total_c_qtd = 0
        total_c_prob = 0.0
        total_alunos = 0

        # Para exibição: usa conceito_id e periodicidade do primeiro vínculo (ou mais representativo)
        vinc_ref, conceito_ref = pares[0]
        # Se há só um vínculo, usa seu periodo_sugerido; se há vários, não exibe (None)
        periodo_sugerido = vinc_ref.periodo_sugerido if len(pares) == 1 else None
        periodicidade_oferta = vinc_ref.periodicidade_oferta if len(pares) == 1 else "ambos"

        for vinc, conceito in pares:
            dados = _calcular_demanda_por_vinculo(db, vinc.curso_codigo, vinc.conceito_id, periodo_atual, context_cache)
            dados["disciplina_codigo"] = mapa_codigos.get((vinc.curso_codigo, vinc.conceito_id), vinc.conceito_id)
            demanda_por_curso.append(dados)
            total_a_qtd += dados["grupo_a_qtd"]
            total_a_prob += dados["grupo_a_prob"]
            total_b += dados["grupo_b_qtd"]
            total_c_qtd += dados["grupo_c_qtd"]
            total_c_prob += dados["grupo_c_prob"]
            total_alunos += dados["total_alunos"]

        demanda_total = round(total_a_prob + total_b + total_c_prob, 2)
        cod_ref = mapa_codigos.get((vinc_ref.curso_codigo, conceito_ref.id), conceito_ref.id)

        resultado.append({
            # Usa conceito_id do primeiro curso como referência; demanda_por_curso tem todos
            "conceito_id": conceito_ref.id,
            "disciplina_codigo": cod_ref,
            "disciplina_nome": nome_normalizado,
            "periodo_sugerido": periodo_sugerido,
            "periodicidade_oferta": periodicidade_oferta,
            "grupo_a_qtd": total_a_qtd,
            "grupo_b_qtd": total_b,
            "grupo_c_qtd": total_c_qtd,
            "demanda_estimada": demanda_total,
            "total_alunos": total_alunos,
            # RF12 — quebra por curso
            "demanda_por_curso": demanda_por_curso,
        })

    return resultado


@router.get("/detalhe")
def obter_detalhe_demanda(
    curso_codigo: str,
    conceito_id: str,
    periodo_atual: str,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """Retorna os detalhes de alunos, probabilidades, curso e semestre de uma disciplina específica."""
    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(db, "consulta_detalhe_demanda", f"Curso: {curso_codigo}, Conceito: {conceito_id}, Periodo: {periodo_atual}", usr_id)

    # 1. Busca o conceito de referência
    conceito = db.query(ConceitoDisciplina).filter(
        ConceitoDisciplina.id == conceito_id,
    ).first()

    if not conceito:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disciplina '{conceito_id}' não encontrada.",
        )

    # 2. Se o conceito_id for de outro curso, localiza o conceito equivalente deste curso_codigo pelo nome
    conceito_alvo = db.query(ConceitoDisciplina).filter(
        ConceitoDisciplina.curso_codigo == curso_codigo,
        ConceitoDisciplina.nome_normalizado == conceito.nome_normalizado,
    ).first() or conceito

    conceito_id_efetivo = conceito_alvo.id

    # 3. Busca informações do curso e do vínculo curricular
    curso = db.query(Curso).filter(Curso.codigo == curso_codigo).first()
    vinculo = db.query(VinculoCurricular).filter(
        VinculoCurricular.curso_codigo == curso_codigo,
        VinculoCurricular.conceito_id == conceito_id_efetivo,
    ).first()

    cod_oficial = _obter_codigo_disciplina(db, curso_codigo, conceito_id_efetivo)

    context_cache = inicializar_context_cache(db, curso_codigo)

    if not _tem_dados_academicos(db, context_cache) or not _periodo_possui_dados(db, periodo_atual, context_cache):
        ga = []
        gb = []
        gc = []
        prob_a = 0.0
        prob_c = 0.0
        total = 0.0
    else:
        periodo_cursando = obter_periodo_cursando_referencia(db, periodo_atual, curso_codigo, context_cache)
        ga = grupo_a(db, curso_codigo, conceito_id_efetivo, periodo_cursando, context_cache)
        gb = grupo_b(db, curso_codigo, conceito_id_efetivo, context_cache)
        gc = grupo_c(db, curso_codigo, conceito_id_efetivo, periodo_cursando, context_cache)
        prob_a = sum(aluno.probabilidade_reprovacao for aluno in ga)
        prob_c = sum(aluno.probabilidade_aprovacao for aluno in gc)
        total = prob_a + len(gb) + prob_c

    return {
        "conceito_id": conceito_id_efetivo,
        "disciplina_codigo": cod_oficial,
        "disciplina_nome": conceito_alvo.nome_normalizado,
        "curso_codigo": curso_codigo,
        "curso_nome": curso.nome if curso else curso_codigo,
        "periodo_sugerido": vinculo.periodo_sugerido if vinculo else None,
        "periodicidade_oferta": vinculo.periodicidade_oferta if vinculo else None,
        "demanda_estimada": round(total, 2),
        "total_alunos": len(ga) + len(gb) + len(gc),
        "grupo_a": [
            {"matricula": aluno.matricula, "probabilidade": aluno.probabilidade_reprovacao, "probabilidade_reprovacao": aluno.probabilidade_reprovacao}
            for aluno in ga
        ],
        "grupo_b": gb,
        "grupo_c": [
            {"matricula": aluno.matricula, "probabilidade": aluno.probabilidade_aprovacao, "probabilidade_aprovacao": aluno.probabilidade_aprovacao}
            for aluno in gc
        ],
    }


@router.get("/exportar")
def exportar_demandas_csv(
    curso_codigo: str,
    periodo_atual: str,
    modo: str = "regular",
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """Gera um arquivo CSV formatado com a estimativa de demanda do curso no período."""
    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(db, "exportacao_csv", f"Curso: {curso_codigo}, Periodo: {periodo_atual}", usr_id)

    # Reutiliza a lógica de obter_demandas para garantir consistência
    if curso_codigo == "TODOS":
        demandas = _obter_demandas_todos_cursos(db, periodo_atual)
    else:
        vinculos_query = (
            db.query(VinculoCurricular)
            .join(ConceitoDisciplina, VinculoCurricular.conceito_id == ConceitoDisciplina.id)
            .filter(VinculoCurricular.curso_codigo == curso_codigo)
            .all()
        )

        if not vinculos_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum vínculo curricular encontrado para o curso '{curso_codigo}'",
            )

        vinculos = list(vinculos_query)
        mapa_codigos = _mapear_codigos_disciplina(db, curso_codigo)
        demandas = []
        for vinc in vinculos:
            conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == vinc.conceito_id).first()
            if not conceito:
                continue
            dados = _calcular_demanda_por_vinculo(db, curso_codigo, vinc.conceito_id, periodo_atual)
            cod_oficial = mapa_codigos.get((curso_codigo, vinc.conceito_id), vinc.conceito_id)
            dados["disciplina_codigo"] = cod_oficial
            demandas.append({
                "conceito_id": vinc.conceito_id,
                "disciplina_codigo": cod_oficial,
                "disciplina_nome": conceito.nome_normalizado,
                "periodo_sugerido": vinc.periodo_sugerido,
                **dados,
                "demanda_por_curso": [dados],
            })

    # Escreve o CSV na memória
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")

    # Cabeçalho
    writer.writerow([
        "Codigo Disciplina", "Nome Disciplina", "Periodo Sugerido",
        "Curso", "Grupo A (Cursando)", "Grupo B (Aptos)", "Grupo C (Potenciais)", "Demanda Estimada"
    ])

    for item in demandas:
        for dpc in item.get("demanda_por_curso", []):
            cod_disc = dpc.get("disciplina_codigo") or item.get("disciplina_codigo") or item["conceito_id"]
            writer.writerow([
                cod_disc,
                item["disciplina_nome"],
                item.get("periodo_sugerido") or "-",
                dpc["curso_codigo"],
                dpc["grupo_a_qtd"],
                dpc["grupo_b_qtd"],
                dpc["grupo_c_qtd"],
                dpc["demanda_estimada"],
            ])

    output.seek(0)

    # Retorna o arquivo como stream para download
    filename = f"demanda_{curso_codigo}_{periodo_atual.replace('/', '-')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Encoding": "utf-8"
        }
    )


class RemoverMatriculaRequest(BaseModel):
    matricula: str
    curso_codigo: str
    conceito_id: str
    periodo_atual: str
    justificativa: str = ""


@router.post("/remover-matricula")
def remover_matricula_cursando(
    req: RemoverMatriculaRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Permite à coordenação remover a matrícula de um aluno que está cursando (Grupo A),
    por motivo de desistência, cancelamento ou trancamento conhecido fora dos relatórios.
    """
    nome_alvo = _obter_nome_normalizado(db, req.conceito_id)
    if not nome_alvo:
        conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == req.conceito_id).first()
        nome_alvo = conceito.nome_normalizado if conceito else None

    cods = _obter_codigos_disciplina(db, req.curso_codigo, nome_alvo) if nome_alvo else []
    if not cods:
        cods_direto = [r[0] for r in db.query(CodigoDisciplina.codigo).filter(
            CodigoDisciplina.curso_codigo == req.curso_codigo,
            CodigoDisciplina.conceito_id == req.conceito_id,
        ).all()]
        cods = cods_direto or [req.conceito_id]

    formatos = _formatos_periodo(req.periodo_atual)

    # Busca o registro em historico com situacao 'cursando'
    registros = db.query(Historico).filter(
        Historico.aluno_matricula == req.matricula,
        Historico.curso_codigo == req.curso_codigo,
        Historico.disciplina_codigo.in_(cods),
        Historico.situacao == "cursando",
        Historico.periodo_letivo.in_(formatos),
    ).all()

    if not registros:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum registro de matrícula 'cursando' encontrado para o aluno {req.matricula} nesta disciplina no período {req.periodo_atual}.",
        )

    for reg in registros:
        reg.situacao = "trancado"
        motivo = req.justificativa.strip() if req.justificativa else "Desistência / Trancamento informado pela coordenação"
        reg.situacao_matricula = f"Removido pela coordenação: {motivo}"

    db.commit()

    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(
        db,
        "remocao_matricula_cursando",
        f"Matrícula: {req.matricula}, Curso: {req.curso_codigo}, Conceito: {req.conceito_id}, Período: {req.periodo_atual}, Motivo: {req.justificativa}",
        usr_id,
    )

    return {
        "status": "ok",
        "message": f"Matrícula {req.matricula} removida com sucesso da disciplina no período {req.periodo_atual}.",
    }

