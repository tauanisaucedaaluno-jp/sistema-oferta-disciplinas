"""
ETL de importação dos CSVs de histórico escolar, um arquivo por curso (RF02).
"""
import re
import os
import pandas as pd
from typing import Dict, List, Set, Tuple
from sqlalchemy.orm import Session

from db.models import Aluno, Historico, VinculoCurricular, CodigoDisciplina

# Reutiliza normalizador de nome se necessário, mas histórico grava código bruto
from etl.importar_curriculo import EXCECOES


def obter_tipo_semestre(periodo_str: str) -> str:
    """Retorna 'impar' ou 'par' baseando-se no texto do período letivo."""
    if not isinstance(periodo_str, str):
        return ""
    p = periodo_str.lower()
    if "1." in p or "1o" in p or "1º" in p or "impar" in p or p.endswith("/1") or p == "1":
        return "impar"
    if "2." in p or "2o" in p or "2º" in p or "par" in p or p.endswith("/2") or p == "2":
        return "par"
    return ""


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    def _match(col: str) -> str:
        col_norm = col.lower().strip()
        import unicodedata
        col_norm = unicodedata.normalize('NFKD', col_norm).encode('ASCII', 'ignore').decode('ASCII')
        if 'mat' in col_norm:
            if 'situ' in col_norm:
                return 'situacao_da_matricula'
            return 'matricula'
        if 'disciplina' in col_norm or 'ativ' in col_norm:
            if 'situ' in col_norm:
                return 'situacao_na_disciplina'
            if 'nome' in col_norm:
                return 'nome_ativ_curric'
            if 'cod' in col_norm:
                return 'cod_ativ_curric'
        if 'curso' in col_norm:
            return 'cod_curso'
        if 'ppc' in col_norm or 'vers' in col_norm:
            return 'versao_ppc'
        if 'ano' in col_norm:
            return 'ano'
        if 'periodo' in col_norm or 'perio' in col_norm:
            return 'periodo'
        return col
    df = df.copy()
    df.columns = [_match(col) for col in df.columns]
    return df


def ler_historico(caminho: str) -> pd.DataFrame:
    """Lê histórico escolar de arquivos CSV (latin-1 ou utf-8) ou Excel."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(caminho)
    else:
        try:
            df = pd.read_csv(caminho, sep=';', encoding='utf-8')
        except (UnicodeDecodeError, ValueError):
            df = pd.read_csv(caminho, sep=';', encoding='latin-1')
    return normalizar_colunas(df)


def normalizar_situacao(df: pd.DataFrame) -> pd.DataFrame:
    """RF03, RN04: Mapeia os estados originais da disciplina para os 5 estados canônicos."""
    if df.empty:
        return df
        
    # Mapeamento oficial (RN04)
    mapping = {
        "aprovado com nota": "aprovado",
        "aprovado sem nota": "aprovado",
        "aproveitamento": "aprovado",
        "aproveitamento de creditos": "aprovado",
        "dispensado com nota": "aprovado",
        "dispensado sem nota": "aprovado",
        
        "reprovado com nota": "reprovado",
        "reprovado por frequencia": "reprovado",
        "reprovado sem nota": "reprovado",
        
        "matricula": "cursando",
        
        "trancamento parcial": "trancado",
        "trancamento total": "trancado",
        "trancamento por estado de calamidade publica": "trancado",
        
        "sod": "indefinido",
        "disciplina nao concluida": "indefinido",
        "incompleto": "indefinido",
        "mobilidade academica": "indefinido"
    }

    def _normalize(val):
        if pd.isna(val):
            return "indefinido"
        val_str = str(val).lower().strip()
        # Remove acentos
        import unicodedata
        val_str = unicodedata.normalize('NFKD', val_str).encode('ASCII', 'ignore').decode('ASCII')
        return mapping.get(val_str, "indefinido")

    df = df.copy()
    col_sit = 'situacao_na_disciplina'
    df['situacao_canoniva'] = df[col_sit].apply(_normalize)
    return df


def excluir_evadidos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna o DataFrame.
    RN05 diz que alunos evadidos devem ser excluídos das análises dos Grupos B e C,
    mas os seus registros de histórico continuam sendo mantidos no banco para auditoria.
    Portanto, esta função apenas retorna o próprio DataFrame.
    A filtragem por evasão é realizada dinamicamente em tempo de execução/consulta.
    """
    return df


def inferir_periodicidade(db: Session, df_historico: pd.DataFrame, conceitos: Dict[Tuple[str, str], str]):
    """RN03: Infere se a disciplina é ofertada em semestre ímpar, par ou ambos."""
    col_hist_cod = 'cod_ativ_curric'
    col_periodo = 'periodo'
    
    # Dicionário de (curso, conceito_id) -> set de semestres letivos observados ('impar', 'par')
    observacoes: Dict[Tuple[str, str], Set[str]] = {}
    
    for _, row in df_historico.iterrows():
        curso = str(row['cod_curso'])
        codigo = str(row[col_hist_cod])
        c_id = conceitos.get((curso, codigo))
        
        if not c_id:
            continue
            
        periodo_tipo = obter_tipo_semestre(row[col_periodo])
        if not periodo_tipo:
            continue
            
        chave = (curso, c_id)
        if chave not in observacoes:
            observacoes[chave] = set()
        observacoes[chave].add(periodo_tipo)
        
    for (curso, c_id), semestres in observacoes.items():
        if "impar" in semestres and "par" in semestres:
            periodicidade = "ambos"
        elif "impar" in semestres:
            periodicidade = "impar"
        elif "par" in semestres:
            periodicidade = "par"
        else:
            continue
            
        # Busca o VinculoCurricular e atualiza a periodicidade
        vinc = db.query(VinculoCurricular).filter(
            VinculoCurricular.curso_codigo == curso,
            VinculoCurricular.conceito_id == c_id
        ).first()
        
        if vinc:
            vinc.periodicidade_oferta = periodicidade
            
    db.commit()


def gravar_historico(db: Session, df: pd.DataFrame, conceitos: Dict[Tuple[str, str], str]):
    """Insere ou atualiza os históricos e alunos no banco de dados."""
    col_mat = 'matricula'
    col_hist_cod = 'cod_ativ_curric'
    col_periodo = 'periodo'
    col_ano = 'ano'
    col_sit_mat = 'situacao_da_matricula'
    
    # 1. Garante que todos os alunos vistos no histórico existam no banco
    alunos_unicos = df[[col_mat, 'cod_curso']].drop_duplicates()
    for _, row in alunos_unicos.iterrows():
        mat = str(row[col_mat])
        curso = str(row['cod_curso'])
        
        aluno_existente = db.query(Aluno).filter(Aluno.matricula == mat).first()
        if not aluno_existente:
            # Obtém semestre de ingresso a partir do primeiro registro histórico
            match = df[df[col_mat] == row[col_mat]].sort_values(by=['ano', col_periodo])
            ingresso = "2023/1"
            if not match.empty:
                primeiro_ano = match.iloc[0]['ano']
                primeiro_per = match.iloc[0][col_periodo]
                sem_tipo = "1" if obter_tipo_semestre(primeiro_per) == "impar" else "2"
                ingresso = f"{primeiro_ano}/{sem_tipo}"
                
            aluno_novo = Aluno(
                matricula=mat,
                curso_codigo=curso,
                semestre_ingresso=ingresso
            )
            db.add(aluno_novo)
    db.commit()

    # 2. Grava cada linha de histórico
    for _, row in df.iterrows():
        mat = str(row[col_mat])
        curso = str(row['cod_curso'])
        codigo = str(row[col_hist_cod])
        ano = int(row[col_ano])
        per = str(row[col_periodo])
        
        # Converte para formato ex: 2026/1
        sem_tipo = "1" if obter_tipo_semestre(per) == "impar" else "2"
        periodo_letivo = f"{ano}/{sem_tipo}"
        
        situacao_canon = row['situacao_canoniva']
        situacao_mat = str(row[col_sit_mat]) if pd.notna(row[col_sit_mat]) else "Aluno Regular"

        # Verifica se o código resolve para algum conceito conhecido
        c_id = conceitos.get((curso, codigo))
        if not c_id:
            msg = f"Aviso: Linha de histórico para código {codigo} (curso {curso}) não pôde ser associada a nenhum conceito conhecido."
            EXCECOES.append(msg)

        # Insere histórico
        hist_novo = Historico(
            aluno_matricula=mat,
            curso_codigo=curso,
            disciplina_codigo=codigo,
            periodo_letivo=periodo_letivo,
            situacao=situacao_canon,
            situacao_matricula=situacao_mat
        )
        db.add(hist_novo)
        
    db.commit()
