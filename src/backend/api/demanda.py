import csv
import io
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Curso, VinculoCurricular, ConceitoDisciplina, Usuario
from api.auth import obter_usuario_atual
from api.deps import registrar_acesso
from core.groups import grupo_a, grupo_b, grupo_c

router = APIRouter()


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


def _calcular_demanda_por_vinculo(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str, context_cache: dict = None) -> dict:
    """Calcula A, B, C e demanda estimada para um par (curso, conceito)."""
    ga = grupo_a(db, curso_codigo, conceito_id, periodo_atual, context_cache)
    gb = grupo_b(db, curso_codigo, conceito_id, context_cache)
    gc = grupo_c(db, curso_codigo, conceito_id, periodo_atual, context_cache)
    prob_c = sum(aluno.probabilidade_aprovacao for aluno in gc)
    total_ponderado = len(ga) + len(gb) + prob_c
    return {
        "curso_codigo": curso_codigo,
        "grupo_a_qtd": len(ga),
        "grupo_b_qtd": len(gb),
        "grupo_c_qtd": len(gc),
        "grupo_c_prob": round(prob_c, 2),
        # RF11: soma ponderada (A + B + Σ prob C) — pode ser decimal
        "demanda_estimada": round(total_ponderado, 2),
        # Contagem inteira de alunos distintos (A + B + C sem ponderação)
        "total_alunos": len(ga) + len(gb) + len(gc),
    }


def _filtrar_vinculos_por_modo(vinculos, modo: str, periodo_atual: str):
    """Aplica filtro de modo extraordinário se necessário (RN02 / RF06).

    Aceita tanto objetos VinculoCurricular puros quanto tuplas (VinculoCurricular, ConceitoDisciplina).
    Suporta formatos como '2026/1', '2026/01', '20261' (ímpar) e '2026/2', '2026/02', '20262' (par).
    """
    if modo == "extraordinaria":
        p_clean = periodo_atual.replace("/", "").strip()
        semestre_tipo = "impar" if p_clean.endswith("1") or p_clean.endswith("01") else "par"
        vinculos = [
            v for v in vinculos
            if _get_vinculo(v).periodicidade_oferta is not None
            and _get_vinculo(v).periodicidade_oferta != "ambos"
            and _get_vinculo(v).periodicidade_oferta != semestre_tipo
        ]
    return vinculos


def _get_vinculo(item):
    """Extrai o VinculoCurricular de um item que pode ser o objeto direto ou uma tupla."""
    return item[0] if isinstance(item, tuple) else item


@router.get("")
def obter_demandas(
    curso_codigo: str,
    periodo_atual: str,
    modo: str = "regular",
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Retorna o cálculo de demanda de todas as disciplinas vinculadas ao curso no período.

    Quando curso_codigo == 'TODOS', consolida todas as disciplinas de todos os cursos,
    agrupando por nome_normalizado (RF12). Cada item do resultado inclui 'demanda_por_curso'
    com a quebra individual por curso.
    """
    usr_id = usuario_atual.id if usuario_atual else None
    registrar_acesso(db, "consulta_demanda", f"Curso: {curso_codigo}, Periodo: {periodo_atual}, Modo: {modo}", usr_id)

    if curso_codigo == "TODOS":
        return _obter_demandas_todos_cursos(db, periodo_atual, modo)

    # --- Modo por curso específico ---
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

    vinculos = _filtrar_vinculos_por_modo(list(vinculos_query), modo, periodo_atual)

    context_cache = {}
    resultado = []
    for vinc in vinculos:
        conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == vinc.conceito_id).first()
        if not conceito:
            continue

        dados_curso = _calcular_demanda_por_vinculo(db, curso_codigo, vinc.conceito_id, periodo_atual, context_cache)

        resultado.append({
            "conceito_id": vinc.conceito_id,
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


def _obter_demandas_todos_cursos(db: Session, periodo_atual: str, modo: str):
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

    todos_vinculos = _filtrar_vinculos_por_modo(
        [(v, c) for v, c in todos_vinculos],
        modo,
        periodo_atual,
    )

    # Agrupa por nome_normalizado (disciplinas "iguais" em cursos diferentes)
    # Estrutura: {nome_normalizado: [(vinculo, conceito), ...]}
    grupos_por_nome: dict = defaultdict(list)
    for vinc, conceito in todos_vinculos:
        grupos_por_nome[conceito.nome_normalizado].append((vinc, conceito))

    context_cache = {}
    resultado = []
    for nome_normalizado, pares in sorted(grupos_por_nome.items()):
        demanda_por_curso = []
        total_a = 0
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
            demanda_por_curso.append(dados)
            total_a += dados["grupo_a_qtd"]
            total_b += dados["grupo_b_qtd"]
            total_c_qtd += dados["grupo_c_qtd"]
            total_c_prob += dados["grupo_c_prob"]
            total_alunos += dados["total_alunos"]

        demanda_total = round(total_a + total_b + total_c_prob, 2)

        resultado.append({
            # Usa conceito_id do primeiro curso como referência; demanda_por_curso tem todos
            "conceito_id": conceito_ref.id,
            "disciplina_nome": nome_normalizado,
            "periodo_sugerido": periodo_sugerido,
            "periodicidade_oferta": periodicidade_oferta,
            "grupo_a_qtd": total_a,
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

    ga = grupo_a(db, curso_codigo, conceito_id_efetivo, periodo_atual)
    gb = grupo_b(db, curso_codigo, conceito_id_efetivo)
    gc = grupo_c(db, curso_codigo, conceito_id_efetivo, periodo_atual)
    total = len(ga) + len(gb) + sum(aluno.probabilidade_aprovacao for aluno in gc)

    return {
        "conceito_id": conceito_id_efetivo,
        "disciplina_nome": conceito_alvo.nome_normalizado,
        "curso_codigo": curso_codigo,
        "curso_nome": curso.nome if curso else curso_codigo,
        "periodo_sugerido": vinculo.periodo_sugerido if vinculo else None,
        "periodicidade_oferta": vinculo.periodicidade_oferta if vinculo else None,
        "demanda_estimada": round(total, 2),
        "total_alunos": len(ga) + len(gb) + len(gc),
        "grupo_a": ga,
        "grupo_b": gb,
        "grupo_c": [
            {"matricula": aluno.matricula, "probabilidade": aluno.probabilidade_aprovacao}
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
    registrar_acesso(db, "exportacao_csv", f"Curso: {curso_codigo}, Periodo: {periodo_atual}, Modo: {modo}", usr_id)

    # Reutiliza a lógica de obter_demandas para garantir consistência
    if curso_codigo == "TODOS":
        demandas = _obter_demandas_todos_cursos(db, periodo_atual, modo)
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

        vinculos = _filtrar_vinculos_por_modo(list(vinculos_query), modo, periodo_atual)
        demandas = []
        for vinc in vinculos:
            conceito = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == vinc.conceito_id).first()
            if not conceito:
                continue
            dados = _calcular_demanda_por_vinculo(db, curso_codigo, vinc.conceito_id, periodo_atual)
            demandas.append({
                "conceito_id": vinc.conceito_id,
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
            writer.writerow([
                item["conceito_id"],
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
