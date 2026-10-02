"""
Módulo de API para upload e importação de novos históricos escolares e currículos (RF01, RF02, RNF07).
Permite à coordenação atualizar os dados do sistema mantendo o tempo de execução bem abaixo de 4 minutos.
"""
import os
import time
import shutil
import tempfile
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db.database import get_db
from db.models import (
    Usuario,
    Curso,
    ConceitoDisciplina,
    CodigoDisciplina,
    VinculoCurricular,
    PreRequisito,
    Aluno,
    Historico,
    PeriodoLetivo,
    DemandaSnapshot,
)
from api.auth import obter_usuario_atual
from api.deps import registrar_acesso
from etl.importar_curriculo import (
    ler_csv_curriculo,
    deduplicar_versoes,
    construir_conceitos,
    montar_vinculos_curriculares,
    montar_pre_requisitos,
    relatorio_excecoes as relatorio_curriculo_excecoes,
    EXCECOES,
)
from etl.importar_historico import (
    ler_historico,
    normalizar_situacao,
    excluir_evadidos,
    filtrar_por_ano_corte,
    inferir_periodicidade,
    gravar_historico,
)

router = APIRouter()



def _limpar_tabelas_academicas(db: Session):
    """Limpa tabelas acadêmicas para recarga completa sem inconsistências ou dados órfãos."""
    if db.bind and db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("TRUNCATE TABLE pre_requisito, vinculo_curricular, codigo_disciplina, conceito_disciplina, historico, aluno, curso CASCADE;"))
        db.commit()
    else:
        db.query(PreRequisito).delete()
        db.query(VinculoCurricular).delete()
        db.query(CodigoDisciplina).delete()
        db.query(ConceitoDisciplina).delete()
        db.query(Historico).delete()
        db.query(Aluno).delete()
        db.query(Curso).delete()
        db.commit()



def _salvar_snapshots_demanda(db: Session, periodo_alvo: str = None, sobrescrever: bool = False, usuario_id: int = 1):
    """
    Calcula e armazena o snapshot de demanda (Grupos A, B, C) por período letivo e usuário.
    Se periodo_alvo for informado, processa apenas esse período.
    Se um período já possuir snapshot e sobrescrever=False, seu snapshot é rigorosamente PRESERVADO,
    garantindo que uma importação de 2027/1 NUNCA altere os dados gravados de 2026/1.
    """
    import sys, os
    BASE_DIR_LOCAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if BASE_DIR_LOCAL not in sys.path:
        sys.path.insert(0, BASE_DIR_LOCAL)

    from core.groups import inicializar_context_cache, grupo_a, grupo_b, grupo_c, obter_periodo_cursando_referencia

    periodos = db.query(PeriodoLetivo).filter(PeriodoLetivo.usuario_id == usuario_id).all()
    if periodo_alvo:
        periodos = [p for p in periodos if p.codigo == periodo_alvo]
        if not periodos:
            p_obj = db.query(PeriodoLetivo).filter(PeriodoLetivo.usuario_id == usuario_id, PeriodoLetivo.codigo == periodo_alvo).first()
            if p_obj:
                periodos = [p_obj]

    vinculos = db.query(VinculoCurricular).all()
    cursos_unicos = list(set(v.curso_codigo for v in vinculos))

    caches_por_curso = {}
    for curso_cod in cursos_unicos:
        try:
            caches_por_curso[curso_cod] = inicializar_context_cache(db, curso_cod)
        except Exception:
            caches_por_curso[curso_cod] = {}

    for periodo in periodos:
        # Se o período já possui snapshots e não foi solicitada a sobrescrita, preserva intacto
        ja_tem = db.query(DemandaSnapshot).filter(
            DemandaSnapshot.usuario_id == usuario_id,
            DemandaSnapshot.periodo_codigo == periodo.codigo,
        ).first() is not None
        if ja_tem and not sobrescrever:
            continue

        # Remove apenas snapshots deste período específico do usuário antes de salvar o novo
        db.query(DemandaSnapshot).filter(
            DemandaSnapshot.usuario_id == usuario_id,
            DemandaSnapshot.periodo_codigo == periodo.codigo,
        ).delete(synchronize_session=False)
        db.flush()

        novos = []
        for vinc in vinculos:
            curso_cod = vinc.curso_codigo
            conceito_id = vinc.conceito_id
            cache = caches_por_curso.get(curso_cod, {})
            try:
                periodo_cursando = obter_periodo_cursando_referencia(db, periodo.codigo, curso_cod, cache)
                ga = grupo_a(db, curso_cod, conceito_id, periodo_cursando, cache)
                gb = grupo_b(db, curso_cod, conceito_id, cache)
                gc = grupo_c(db, curso_cod, conceito_id, periodo_cursando, cache)
                prob_a = round(sum(a.probabilidade_reprovacao for a in ga), 2)
                prob_c = round(sum(c.probabilidade_aprovacao for c in gc), 2)
                demanda = round(prob_a + len(gb) + prob_c, 2)
            except Exception:
                ga, gb, gc = [], [], []
                prob_a, prob_c, demanda = 0.0, 0.0, 0.0

            novos.append(DemandaSnapshot(
                usuario_id=usuario_id,
                periodo_codigo=periodo.codigo,
                curso_codigo=curso_cod,
                conceito_id=conceito_id,
                grupo_a_qtd=len(ga),
                grupo_b_qtd=len(gb),
                grupo_c_qtd=len(gc),
                grupo_a_prob=prob_a,
                grupo_c_prob=prob_c,
                demanda_estimada=demanda,
            ))

        if novos:
            db.bulk_save_objects(novos)
        db.commit()


MINIMO_ARQUIVOS_HISTORICO = 6


@router.post("/upload")
async def upload_arquivos_academicos(
    historicos: List[UploadFile] = File(..., description="Arquivos CSV de histórico escolar por curso (mínimo de 6 arquivos obrigatórios)"),
    curriculo: Optional[UploadFile] = File(None, description="Arquivo CSV opcional de matriz curricular"),
    periodo: Optional[str] = Form(None, description="Período acadêmico de destino (ex.: '2027/1')"),
    ignorar_minimo: bool = False,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Recebe os arquivos CSV de histórico escolar (e opcionalmente o de currículo)
    e executa o pipeline otimizado de importação (ETL).
    Exige no mínimo 6 arquivos CSV de histórico escolar para garantir a integridade
    de todos os cursos do campus e semestres anteriores.
    """
    if not historicos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum arquivo de histórico foi enviado.",
        )

    if len(historicos) < MINIMO_ARQUIVOS_HISTORICO and not ignorar_minimo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Importação não permitida: É obrigatório enviar no mínimo {MINIMO_ARQUIVOS_HISTORICO} arquivos CSV de histórico escolar "
                f"(um para cada curso disponível no sistema: ALEA, ALEC, ALEE, ALEM, ALES e ALET). "
                f"Foram enviados apenas {len(historicos)} arquivo(s). A ação foi cancelada para preservar a integridade dos dados."
            ),
        )

    t0 = time.time()
    EXCECOES.clear()
    temp_dir = tempfile.mkdtemp(prefix="upload_oferta_")

    try:
        # 1. Salva os arquivos de histórico temporários
        caminhos_historicos = []
        for hist in historicos:
            if not hist.filename.lower().endswith((".csv", ".xlsx", ".xls")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Arquivo inválido '{hist.filename}'. Apenas arquivos .csv ou .xlsx são aceitos.",
                )
            dest_path = os.path.join(temp_dir, hist.filename)
            with open(dest_path, "wb") as f_out:
                content = await hist.read()
                f_out.write(content)
            caminhos_historicos.append(dest_path)

        # 2. Localiza ou salva o arquivo de currículo
        caminho_curriculo = None
        if curriculo and curriculo.filename:
            caminho_curriculo = os.path.join(temp_dir, curriculo.filename)
            with open(caminho_curriculo, "wb") as f_out:
                content = await curriculo.read()
                f_out.write(content)
        else:
            # Reutiliza o currículo existente em data/raw ou data/sample
            candidatos = [
                os.path.join(BASE_DIR, "data", "raw", "4284_Currículo Cursos.csv"),
                os.path.join(BASE_DIR, "data", "sample", "curriculo_sample.csv"),
            ]
            for cand in candidatos:
                if os.path.exists(cand):
                    caminho_curriculo = cand
                    break

        if not caminho_curriculo or not os.path.exists(caminho_curriculo):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum arquivo de currículo foi fornecido e o currículo base padrão não foi encontrado.",
            )

        # 3. Lê o currículo
        df_curriculo_raw = ler_csv_curriculo(caminho_curriculo)
        df_curriculo = deduplicar_versoes(df_curriculo_raw)

        # Diretório persistente de históricos
        dir_raw = os.path.join(BASE_DIR, "data", "raw")
        dir_hist_raw = os.path.join(dir_raw, "historicos")
        os.makedirs(dir_hist_raw, exist_ok=True)

        # Copia os arquivos novos enviados para dir_hist_raw mantendo persistência
        for orig in caminhos_historicos:
            shutil.copy2(orig, os.path.join(dir_hist_raw, os.path.basename(orig)))

        # 4. Lê e consolida os históricos enviados
        dfs_historico = []
        for f in caminhos_historicos:
            df_hist_arq = ler_historico(f)
            dfs_historico.append(df_hist_arq)

        if not dfs_historico:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível processar os arquivos de histórico enviados.",
            )

        df_historico_raw = pd.concat(dfs_historico, ignore_index=True)
        df_historico = normalizar_situacao(df_historico_raw)
        df_historico = excluir_evadidos(df_historico)
        df_historico = filtrar_por_ano_corte(df_historico)

        total_linhas_historico = len(df_historico)
        total_cursando = int((df_historico['situacao_canoniva'] == 'cursando').sum())
        cursos_processados = sorted(list(set(str(c) for c in df_historico['cod_curso'].dropna().unique())))

        # Salva snapshots de todos os períodos existentes ANTES de qualquer alteração,
        # para garantir que semestres anteriores (ex.: 2026/1) fiquem 100% gravados e congelados!
        usr_id = usuario_atual.id if usuario_atual else 1
        _salvar_snapshots_demanda(db, sobrescrever=False, usuario_id=usr_id)

        # 5. Executa a limpeza e recarga: se todos os cursos foram enviados ou se foi enviado currículo, faz recarga completa;
        # caso contrário, limpa apenas os cursos que estão sendo importados, preservando os demais no banco.
        cursos_existentes = set(r[0] for r in db.query(Curso.codigo).all())
        if not cursos_existentes or (curriculo and curriculo.filename) or set(cursos_processados) >= cursos_existentes:
            _limpar_tabelas_academicas(db)
        else:
            db.query(Historico).filter(Historico.curso_codigo.in_(cursos_processados)).delete(synchronize_session=False)
            db.query(Aluno).filter(Aluno.curso_codigo.in_(cursos_processados)).delete(synchronize_session=False)
            db.commit()

        # PASSO 3: Construir Conceitos e Códigos
        conceitos_map = construir_conceitos(db, df_curriculo, df_historico)

        # PASSO 4: Vínculos Curriculares
        montar_vinculos_curriculares(db, df_curriculo, conceitos_map)

        # PASSO 5: Pré-requisitos
        montar_pre_requisitos(db, df_curriculo, conceitos_map)

        # PASSO 6: Gravar Alunos e Histórico
        gravar_historico(db, df_historico, conceitos_map)

        # PASSO 7: Inferir Periodicidade
        inferir_periodicidade(db, df_historico, conceitos_map)

        # PASSO 8: Salvar snapshots de demanda para o período importado
        # Se periodo foi especificado (ex: '2027/1'), salva o snapshot dele com sobrescrever=True.
        # Os semestres anteriores permanecem intocados com seus snapshots originais!
        periodo_alvo_snap = periodo
        if not periodo_alvo_snap:
            curs_rows = df_historico[df_historico['situacao_canoniva'] == 'cursando']
            if not curs_rows.empty and 'periodo_letivo' in curs_rows.columns:
                periodo_alvo_snap = curs_rows['periodo_letivo'].value_counts().index[0]

        if periodo_alvo_snap:
            p_cad = db.query(PeriodoLetivo).filter(
                PeriodoLetivo.usuario_id == usr_id,
                PeriodoLetivo.codigo == periodo_alvo_snap,
            ).first()
            if not p_cad:
                try:
                    import re
                    m = re.match(r"^(\d{4})[./\-]0?([12])$", periodo_alvo_snap.strip())
                    if m:
                        db.add(PeriodoLetivo(
                            usuario_id=usr_id,
                            codigo=periodo_alvo_snap,
                            ano=int(m.group(1)),
                            semestre=int(m.group(2)),
                            descricao=periodo_alvo_snap,
                            is_atual=False,
                        ))
                        db.commit()
                except Exception:
                    pass
            _salvar_snapshots_demanda(db, periodo_alvo=periodo_alvo_snap, sobrescrever=True, usuario_id=usr_id)
        else:
            _salvar_snapshots_demanda(db, sobrescrever=False, usuario_id=usr_id)

        tempo_total = round(time.time() - t0, 2)
        total_alunos = db.query(Aluno).count()

        # Relatório de exceções
        excecoes = relatorio_curriculo_excecoes()
        excecoes_unicas = list(dict.fromkeys(excecoes))

        # Registrar log de auditoria
        usr_id = usuario_atual.id if usuario_atual else None
        registrar_acesso(
            db,
            "upload_historico_academico",
            f"Arquivos: {len(historicos)}, Linhas: {total_linhas_historico}, Alunos: {total_alunos}, Cursando: {total_cursando}, Tempo: {tempo_total}s",
            usr_id,
        )

        msg_retorno = (
            f"Importação concluída com sucesso! {total_linhas_historico:,} registros e {total_alunos:,} alunos consolidados ({len(cursos_processados)} cursos). "
            f"Foram identificadas {total_cursando:,} matrículas ativas em andamento."
            if total_cursando > 0
            else (
                f"Importação concluída! {total_linhas_historico:,} registros processados. "
                "Atenção: nenhuma matrícula ativa ('cursando') foi encontrada nos arquivos. "
                "Os Grupos A (em curso) e C (cursando pré-requisito) exibirão 0; o Grupo B (aptos) foi calculado normalmente."
            )
        )

        return {
            "status": "sucesso",
            "mensagem": msg_retorno,
            "total_arquivos": len(historicos),
            "total_linhas_historico": total_linhas_historico,
            "total_alunos": total_alunos,
            "total_cursando": total_cursando,
            "cursos": cursos_processados,
            "aviso_cursando_zerado": total_cursando == 0,
            "tempo_segundos": tempo_total,
            "total_avisos": len(excecoes_unicas),
            "avisos": excecoes_unicas[:15],
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro durante o processamento do upload: {str(e)}",
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
