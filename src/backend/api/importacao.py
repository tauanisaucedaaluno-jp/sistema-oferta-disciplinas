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
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
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
    db.query(PreRequisito).delete()
    db.query(VinculoCurricular).delete()
    db.query(CodigoDisciplina).delete()
    db.query(ConceitoDisciplina).delete()
    db.query(Historico).delete()
    db.query(Aluno).delete()
    db.query(Curso).delete()
    db.commit()


@router.post("/upload")
async def upload_arquivos_academicos(
    historicos: List[UploadFile] = File(..., description="Arquivos CSV de histórico escolar por curso"),
    curriculo: Optional[UploadFile] = File(None, description="Arquivo CSV opcional de matriz curricular"),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
):
    """
    Recebe os arquivos CSV de histórico escolar (e opcionalmente o de currículo)
    e executa o pipeline otimizado de importação (ETL).
    """
    if not historicos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum arquivo de histórico foi enviado.",
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

        # 4. Lê e consolida os históricos
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

        # 5. Executa a limpeza e recarga no banco de dados de forma atômica
        _limpar_tabelas_academicas(db)

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

        tempo_total = round(time.time() - t0, 2)
        total_alunos = db.query(Aluno).count()

        # Copia os arquivos válidos para data/raw para manter persistência
        dir_raw = os.path.join(BASE_DIR, "data", "raw")
        dir_hist_raw = os.path.join(dir_raw, "historicos")
        if os.path.exists(dir_hist_raw):
            for orig in caminhos_historicos:
                shutil.copy2(orig, os.path.join(dir_hist_raw, os.path.basename(orig)))

        # Relatório de exceções
        excecoes = relatorio_curriculo_excecoes()
        excecoes_unicas = list(dict.fromkeys(excecoes))

        # Registrar log de auditoria
        usr_id = usuario_atual.id if usuario_atual else None
        registrar_acesso(
            db,
            "upload_historico_academico",
            f"Arquivos: {len(historicos)}, Linhas: {total_linhas_historico}, Alunos: {total_alunos}, Tempo: {tempo_total}s",
            usr_id,
        )

        return {
            "status": "sucesso",
            "mensagem": "Importação de dados acadêmicos concluída com sucesso!",
            "total_arquivos": len(historicos),
            "total_linhas_historico": total_linhas_historico,
            "total_alunos": total_alunos,
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
