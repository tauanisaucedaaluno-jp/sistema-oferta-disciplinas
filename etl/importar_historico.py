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

        if (c.startswith('mat') or c == 'aluno' or c == 'matricula_aluno') and 'situ' not in c:
            col_map[col] = 'matricula'
        elif c in ('cod_curso', 'codigo_curso', 'id_curso') or (c.startswith('cod') and 'curso' in c):
            col_map[col] = 'cod_curso'
        elif c in ('curso', 'nome_curso'):
            col_map[col] = 'curso'
        elif 'ppc' in c or (c.startswith('vers') and 'ppc' in c):
            col_map[col] = 'versao_ppc'
        elif c in ('ano', 'ano_letivo'):
            col_map[col] = 'ano'
        elif c in ('periodo', 'perio', 'semestre', 'semestre_letivo'):
            col_map[col] = 'periodo'
        elif ('situ' in c or 'status' in c or 'estado' in c) and ('disc' in c or 'ativ' in c or 'materia' in c or 'componente' in c):
            col_map[col] = 'situacao_na_disciplina'
        elif ('situ' in c or 'status' in c or 'estado' in c) and 'mat' in c:
            col_map[col] = 'situacao_da_matricula'
        elif c in ('situacao', 'status', 'situacao_disciplina', 'situacao_final'):
            col_map[col] = 'situacao_na_disciplina'
        elif c in ('cod_ativ_curric', 'cod_disciplina', 'codigo_disciplina', 'cod_disc') or (c.startswith('cod') and ('ativ' in c or 'disc' in c)):
            col_map[col] = 'cod_ativ_curric'
        elif c in ('nome_ativ_curric', 'nome_disciplina', 'disciplina') or (c.startswith('nome') and ('ativ' in c or 'disc' in c)):
            col_map[col] = 'nome_ativ_curric'

    return df.rename(columns=col_map)


def ler_historico(caminho: str) -> pd.DataFrame:
    """Lê histórico escolar de arquivos CSV (latin-1, utf-8, etc.) ou Excel com detecção resiliente de separador."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(caminho)
        return normalizar_colunas(df)

    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    separators = [';', ',', '\t']

    for enc in encodings:
        for sep in separators:
            try:
                df_test = pd.read_csv(caminho, sep=sep, encoding=enc, nrows=10, dtype=str)
                # Verifica se detectou múltiplas colunas válidas
                if len(df_test.columns) > 3:
                    df = pd.read_csv(caminho, sep=sep, encoding=enc, dtype=str)
                    return normalizar_colunas(df)
            except Exception:
                continue

    # Fallback padrão
    try:
        df = pd.read_csv(caminho, sep=';', encoding='utf-8', dtype=str)
    except Exception:
        df = pd.read_csv(caminho, sep=';', encoding='latin-1', dtype=str)
    return normalizar_colunas(df)


def normalizar_situacao(df: pd.DataFrame) -> pd.DataFrame:
    """RF03, RN04: Mapeia os estados originais da disciplina para os 5 estados canônicos de forma resiliente."""
    if df.empty:
        return df

    import unicodedata

    def _normalize(val):
        if pd.isna(val):
            return "indefinido"
        val_str = str(val).strip()
        if not val_str:
            return "indefinido"

        # Converte para minúsculas e remove acentuações e caracteres corrompidos (mojibake / replacement chars)
        v = unicodedata.normalize('NFKD', val_str.lower()).encode('ASCII', 'ignore').decode('ASCII')
        v = re.sub(r'[^a-z0-9_]', ' ', v).strip()
        v = re.sub(r'\s+', ' ', v)

        # 1. Trancamento
        if 'tranc' in v:
            return "trancado"

        # 2. Cursando / Matrícula ativa
        # Cobre: 'matricula', 'matrícula', 'matr?cula', 'matrcula', 'matriculado', 'cursando', 'em curso', 'em andamento', 'inscrito', 'ativa'
        if any(term in v for term in ['matr', 'curs', 'andamento', 'inscrit']):
            return "cursando"

        # 3. Reprovação
        # Cobre: 'reprovado', 'reprovado com nota', 'reprovado por frequencia', 'reprovado por frequ?ncia', 'reprovado sem nota'
        if 'reprov' in v:
            return "reprovado"

        # 4. Aprovação / Aproveitamento / Dispensa
        # Cobre: 'aprovado com nota', 'aprovado sem nota', 'aproveitamento', 'dispensado', etc.
        if any(term in v for term in ['aprov', 'dispens', 'aproveit']):
            return "aprovado"

        # 5. Outros estados que não concluem nem estão em curso (SOD, cancelado, mobilidade, etc.)
        return "indefinido"

    df = df.copy()
    col_sit = 'situacao_na_disciplina'
    if col_sit not in df.columns:
        candidatos = [c for c in df.columns if any(k in str(c).lower() for k in ['situ', 'status', 'estado'])]
        if candidatos:
            col_sit = candidatos[0]
            df['situacao_na_disciplina'] = df[col_sit]
        else:
            raise ValueError(
                "O arquivo selecionado não contém a coluna de situação das disciplinas dos alunos. "
                "Por favor, verifique se o arquivo enviado é de Histórico Escolar (ex.: 'situação na disciplina')."
            )
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

    for row in df_subset.itertuples(index=False):
        curso = str(row[0])
        codigo = str(row[1])
        c_id = conceitos.get((curso, codigo))

        if not c_id:
            continue

        chave = (curso, c_id)
        if chave not in observacoes:
            observacoes[chave] = set()
        observacoes[chave].add(row[3])

    vinc_map = {(v.curso_codigo, v.conceito_id): v for v in db.query(VinculoCurricular).all()}

    for (curso, c_id), semestres in observacoes.items():
        if "impar" in semestres and "par" in semestres:
            periodicidade = "ambos"
        elif "impar" in semestres:
            periodicidade = "impar"
        elif "par" in semestres:
            periodicidade = "par"
        else:
            continue

        vinc = vinc_map.get((curso, c_id))
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
    for row in df_primeiro_reg[[col_mat, col_ano, col_periodo]].itertuples(index=False):
        mat = str(row[0])
        p_ano = str(row[1]) if pd.notna(row[1]) else "2023"
        p_per = str(row[2]) if pd.notna(row[2]) else "1"
        sem_tipo = "1" if obter_tipo_semestre(p_per) == "impar" else "2"
        ingress_map[mat] = f"{p_ano}/{sem_tipo}"

    alunos_unicos = df[[col_mat, col_curso]].drop_duplicates()
    alunos_existentes = set(r[0] for r in db.query(Aluno.matricula).all())
    alunos_a_criar = []

    for row in alunos_unicos[[col_mat, col_curso]].itertuples(index=False):
        mat = str(row[0])
        curso = str(row[1])
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

    # 2. Grava cada linha de histórico em lotes usando bulk_insert_mappings
    print("Gravando registros de histórico...")
    codigos_desconhecidos = set()
    lote_historico = []
    tamanho_lote = 10000
    total_linhas = len(df)

    col_idx_mat = df.columns.get_loc(col_mat)
    col_idx_curso = df.columns.get_loc(col_curso)
    col_idx_codigo = df.columns.get_loc(col_hist_cod)
    col_idx_ano = df.columns.get_loc(col_ano)
    col_idx_periodo = df.columns.get_loc(col_periodo)
    col_idx_sit_canon = df.columns.get_loc('situacao_canoniva')
    col_idx_sit_mat = df.columns.get_loc(col_sit_mat)

    for idx, row in enumerate(df.itertuples(index=False), 1):
        mat = str(row[col_idx_mat])
        curso = str(row[col_idx_curso])
        codigo = str(row[col_idx_codigo])
        
        ano_val = row[col_idx_ano]
        try:
            ano = int(float(ano_val))
        except (ValueError, TypeError):
            ano = 2023
            
        per = str(row[col_idx_periodo])
        sem_tipo = "1" if obter_tipo_semestre(per) == "impar" else "2"
        periodo_letivo = f"{ano}/{sem_tipo}"

        situacao_canon = row[col_idx_sit_canon]
        sit_mat_val = row[col_idx_sit_mat]
        situacao_mat = str(sit_mat_val) if pd.notna(sit_mat_val) else "Aluno Regular"

        c_id = conceitos.get((curso, codigo))
        if not c_id and (curso, codigo) not in codigos_desconhecidos:
            codigos_desconhecidos.add((curso, codigo))
            EXCECOES.append(f"Aviso: Código {codigo} no histórico do curso {curso} não pôde ser associado a nenhum conceito conhecido.")

        lote_historico.append({
            "aluno_matricula": mat,
            "curso_codigo": curso,
            "disciplina_codigo": codigo,
            "periodo_letivo": periodo_letivo,
            "situacao": situacao_canon,
            "situacao_matricula": situacao_mat,
        })

        if len(lote_historico) >= tamanho_lote:
            db.bulk_insert_mappings(Historico, lote_historico)
            db.commit()
            lote_historico = []
            print(f"Progresso histórico: {idx}/{total_linhas} linhas salvas...")

    if lote_historico:
        db.bulk_insert_mappings(Historico, lote_historico)
        db.commit()
        print(f"Progresso histórico: {total_linhas}/{total_linhas} linhas salvas com sucesso.")
