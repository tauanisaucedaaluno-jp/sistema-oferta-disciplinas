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
    col_map = {}
    import unicodedata
    for col in df.columns:
        c = unicodedata.normalize('NFKD', str(col).lower().strip()).encode('ASCII', 'ignore').decode('ASCII')
        c = re.sub(r'[^a-z0-9_]', '_', c).strip('_')

        if c.startswith('mat') and 'situ' not in c:
            col_map[col] = 'matricula'
        elif c == 'cod_curso':
            col_map[col] = 'cod_curso'
        elif c == 'curso':
            col_map[col] = 'curso'
        elif 'ppc' in c or (c.startswith('vers') and 'ppc' in c):
            col_map[col] = 'versao_ppc'
        elif c == 'ano':
            col_map[col] = 'ano'
        elif c in ('periodo', 'perio'):
            col_map[col] = 'periodo'
        elif 'situ' in c and ('disc' in c or 'ativ' in c):
            col_map[col] = 'situacao_na_disciplina'
        elif 'situ' in c and 'mat' in c:
            col_map[col] = 'situacao_da_matricula'
        elif c in ('cod_ativ_curric', 'cod_disciplina') or (c.startswith('cod') and ('ativ' in c or 'disc' in c)):
            col_map[col] = 'cod_ativ_curric'
        elif c in ('nome_ativ_curric', 'nome_disciplina') or (c.startswith('nome') and ('ativ' in c or 'disc' in c)):
            col_map[col] = 'nome_ativ_curric'

    return df.rename(columns=col_map)


def ler_historico(caminho: str) -> pd.DataFrame:
    """Lê histórico escolar de arquivos CSV (latin-1 ou utf-8) ou Excel."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(caminho)
    else:
        try:
            df = pd.read_csv(caminho, sep=';', encoding='utf-8', dtype=str)
        except (UnicodeDecodeError, ValueError):
            df = pd.read_csv(caminho, sep=';', encoding='latin-1', dtype=str)
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
        "dispensado": "aprovado",
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
        "mobilidade academica": "indefinido",
        "situacao da atividade no curriculo": "indefinido"
    }

    import unicodedata
    def _normalize(val):
        if pd.isna(val):
            return "indefinido"
        val_str = str(val).lower().strip()
        val_str = unicodedata.normalize('NFKD', val_str).encode('ASCII', 'ignore').decode('ASCII')
        val_str = re.sub(r'\s+', ' ', val_str)
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


def filtrar_por_ano_corte(df: pd.DataFrame, ano_corte: int = None) -> pd.DataFrame:
    """
    Descarta registros históricos com ano letivo anterior ao ano de corte.
    Evita redundância de dados históricos antigos (ex.: 2006-2015) que já não
    impactam o planejamento presente e futuro de oferta de disciplinas.
    """
    if df.empty or 'ano' not in df.columns:
        return df

    if ano_corte is None:
        try:
            from config import settings
            ano_corte = getattr(settings, "historico_ano_corte", 2016)
        except Exception:
            ano_corte = int(os.getenv("HISTORICO_ANO_CORTE", "2016"))

    def _parse_ano(val):
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return 2026

    mask = df['ano'].apply(_parse_ano) >= ano_corte
    removidas = len(df) - mask.sum()
    if removidas > 0:
        print(f"Filtro de corte ({ano_corte}+): {removidas} registros anteriores a {ano_corte} descartados.")
    return df[mask].copy()


def inferir_periodicidade(db: Session, df_historico: pd.DataFrame, conceitos: Dict[Tuple[str, str], str]):
    """RN03: Infere se a disciplina é ofertada em semestre ímpar, par ou ambos."""
    col_hist_cod = 'cod_ativ_curric'
    col_periodo = 'periodo'
    col_curso = 'cod_curso'

    # Otimização: reduz para linhas únicas de (curso, código, período)
    df_subset = df_historico[[col_curso, col_hist_cod, col_periodo]].dropna().drop_duplicates().copy()
    df_subset['semestre_tipo'] = df_subset[col_periodo].apply(obter_tipo_semestre)
    df_subset = df_subset[df_subset['semestre_tipo'] != '']

    observacoes: Dict[Tuple[str, str], Set[str]] = {}

    for _, row in df_subset.iterrows():
        curso = str(row[col_curso])
        codigo = str(row[col_hist_cod])
        c_id = conceitos.get((curso, codigo))

        if not c_id:
            continue

        chave = (curso, c_id)
        if chave not in observacoes:
            observacoes[chave] = set()
        observacoes[chave].add(row['semestre_tipo'])

    for (curso, c_id), semestres in observacoes.items():
        if "impar" in semestres and "par" in semestres:
            periodicidade = "ambos"
        elif "impar" in semestres:
            periodicidade = "impar"
        elif "par" in semestres:
            periodicidade = "par"
        else:
            continue

        vinc = db.query(VinculoCurricular).filter(
            VinculoCurricular.curso_codigo == curso,
            VinculoCurricular.conceito_id == c_id
        ).first()

        if vinc:
            vinc.periodicidade_oferta = periodicidade

    db.commit()


def gravar_historico(db: Session, df: pd.DataFrame, conceitos: Dict[Tuple[str, str], str]):
    """Insere ou atualiza os históricos e alunos no banco de dados em lotes eficientes."""
    col_mat = 'matricula'
    col_hist_cod = 'cod_ativ_curric'
    col_periodo = 'periodo'
    col_ano = 'ano'
    col_sit_mat = 'situacao_da_matricula'
    col_curso = 'cod_curso'

    # 1. Garante que todos os alunos vistos no histórico existam no banco
    print("Processando alunos...")
    # Determina o semestre de ingresso a partir do registro mais antigo de cada aluno de forma vetorizada
    df_ordenado = df.sort_values(by=[col_ano, col_periodo])
    df_primeiro_reg = df_ordenado.drop_duplicates(subset=[col_mat], keep='first')
    
    ingress_map = {}
    for _, row in df_primeiro_reg.iterrows():
        p_ano = str(row[col_ano]) if pd.notna(row[col_ano]) else "2023"
        p_per = str(row[col_periodo]) if pd.notna(row[col_periodo]) else "1"
        sem_tipo = "1" if obter_tipo_semestre(p_per) == "impar" else "2"
        ingress_map[str(row[col_mat])] = f"{p_ano}/{sem_tipo}"

    alunos_unicos = df[[col_mat, col_curso]].drop_duplicates()
    alunos_existentes = set(r[0] for r in db.query(Aluno.matricula).all())
    alunos_a_criar = []

    for _, row in alunos_unicos.iterrows():
        mat = str(row[col_mat])
        curso = str(row[col_curso])
        if mat not in alunos_existentes:
            ingresso = ingress_map.get(mat, "2023/1")
            alunos_a_criar.append(Aluno(
                matricula=mat,
                curso_codigo=curso,
                semestre_ingresso=ingresso
            ))
            alunos_existentes.add(mat)

    if alunos_a_criar:
        print(f"Inserindo {len(alunos_a_criar)} novos alunos no banco...")
        db.bulk_save_objects(alunos_a_criar)
        db.commit()

    # 2. Grava cada linha de histórico em lotes
    print("Gravando registros de histórico...")
    codigos_desconhecidos = set()
    lote_historico = []
    tamanho_lote = 5000
    total_linhas = len(df)

    for idx, row in enumerate(df.itertuples(index=False), 1):
        mat = str(getattr(row, col_mat))
        curso = str(getattr(row, col_curso))
        codigo = str(getattr(row, col_hist_cod))
        
        try:
            ano = int(float(getattr(row, col_ano)))
        except (ValueError, TypeError):
            ano = 2023
            
        per = str(getattr(row, col_periodo))
        sem_tipo = "1" if obter_tipo_semestre(per) == "impar" else "2"
        periodo_letivo = f"{ano}/{sem_tipo}"

        situacao_canon = getattr(row, 'situacao_canoniva')
        sit_mat_val = getattr(row, col_sit_mat)
        situacao_mat = str(sit_mat_val) if pd.notna(sit_mat_val) else "Aluno Regular"

        c_id = conceitos.get((curso, codigo))
        if not c_id and (curso, codigo) not in codigos_desconhecidos:
            codigos_desconhecidos.add((curso, codigo))
            EXCECOES.append(f"Aviso: Código {codigo} no histórico do curso {curso} não pôde ser associado a nenhum conceito conhecido.")

        hist_novo = Historico(
            aluno_matricula=mat,
            curso_codigo=curso,
            disciplina_codigo=codigo,
            periodo_letivo=periodo_letivo,
            situacao=situacao_canon,
            situacao_matricula=situacao_mat
        )
        lote_historico.append(hist_novo)

        if len(lote_historico) >= tamanho_lote:
            db.bulk_save_objects(lote_historico)
            db.commit()
            lote_historico = []
            print(f"Progresso histórico: {idx}/{total_linhas} linhas salvas...")

    if lote_historico:
        db.bulk_save_objects(lote_historico)
        db.commit()
        print(f"Progresso histórico: {total_linhas}/{total_linhas} linhas salvas com sucesso.")
