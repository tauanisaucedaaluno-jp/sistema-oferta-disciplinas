"""
ETL de importação do CSV de currículo/matriz curricular (RF01).
"""
import re
import unicodedata
from typing import Dict, List, Set, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from db.models import Curso, ConceitoDisciplina, CodigoDisciplina, VinculoCurricular, PreRequisito

# Relatório de exceções global para esta execução
EXCECOES: List[str] = []


def normalizar_nome(nome: str) -> str:
    """Normaliza o nome da disciplina para remover acentos, espaços duplos e pontuação."""
    if not isinstance(nome, str):
        return ""
    nome = nome.upper()
    # Remove acentos
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    # Remove pontuação/caracteres especiais, substituindo por espaço
    nome = re.sub(r'[^A-Z0-9\s]', ' ', nome)
    # Remove espaços duplos e pontas
    return " ".join(nome.split())


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    def _match(col: str) -> str:
        col_norm = col.lower().strip()
        col_norm = unicodedata.normalize('NFKD', col_norm).encode('ASCII', 'ignore').decode('ASCII')
        if 'curso' in col_norm:
            if 'cod' in col_norm:
                return 'cod_curso'
            return 'curso'
        if 'disciplina' in col_norm or 'ativ' in col_norm:
            if 'cod' in col_norm:
                return 'cod_disciplina'
            if 'nome' in col_norm:
                return 'nome_disciplina'
            if 'tipo' in col_norm:
                return 'tipo_disciplina'
        if 'periodo' in col_norm or 'perio' in col_norm:
            return 'periodo_ideal'
        if 'req' in col_norm:
            return 'pre_requisitos'
        if 'equiv' in col_norm:
            return 'equivalencias'
        if 'situ' in col_norm:
            return 'situacao'
        if 'vers' in col_norm:
            return 'num_versao'
        return col
    df = df.copy()
    df.columns = [_match(col) for col in df.columns]
    return df


def ler_csv_curriculo(caminho: str) -> pd.DataFrame:
    """Abre o CSV com separador ';' e encoding 'utf-8' ou 'latin-1'."""
    try:
        df = pd.read_csv(caminho, sep=';', encoding='utf-8')
    except (UnicodeDecodeError, ValueError):
        df = pd.read_csv(caminho, sep=';', encoding='latin-1')
    return normalizar_colunas(df)


def deduplicar_versoes(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas a versão ativa/corrente mais recente de cada disciplina por curso."""
    if df.empty:
        return df

    # Filtra apenas registros ativos
    df_ativos = df[df['situacao'].astype(str).str.upper() == 'ATIVA'].copy()
    if df_ativos.empty:
        df_ativos = df.copy()  # Fallback se nada estiver marcado como ativo

    # Determina a coluna de versão
    col_versao = 'num_versao' if 'num_versao' in df_ativos.columns else ('versao' if 'versao' in df_ativos.columns else None)
    
    if col_versao:
        # Garante tipo numérico para ordenação correta
        df_ativos[col_versao] = pd.to_numeric(df_ativos[col_versao], errors='coerce').fillna(0)
        # Ordena pela versão de forma decrescente
        df_ativos = df_ativos.sort_values(by=col_versao, ascending=False)

    # Deduplica mantendo a primeira ocorrência (a mais recente devido à ordenação)
    df_dedup = df_ativos.drop_duplicates(subset=['cod_curso', 'cod_disciplina'], keep='first')
    return df_dedup


def construir_conceitos(db: Session, df_curriculo: pd.DataFrame, df_historico: pd.DataFrame) -> Dict[Tuple[str, str], str]:
    """
    Agrupa códigos por (curso, nome_normalizado) e equivalências diretas.
    Retorna um mapeamento de (curso_codigo, codigo_disciplina) -> conceito_id.
    """
    # 1. Garante que os cursos referenciados existam no banco
    cursos_unicos = set()
    if 'cod_curso' in df_curriculo.columns:
        cursos_unicos.update(df_curriculo['cod_curso'].dropna().unique())
    if 'cod_curso' in df_historico.columns:
        cursos_unicos.update(df_historico['cod_curso'].dropna().unique())
        
    for cod_curso in cursos_unicos:
        cod_curso_str = str(cod_curso)
        if not db.query(Curso).filter(Curso.codigo == cod_curso_str).first():
            matches = df_curriculo[df_curriculo['cod_curso'] == cod_curso_str]
            curso_nome = matches['curso'].iloc[0] if not matches.empty and 'curso' in df_curriculo.columns else f"Curso {cod_curso_str}"
            if not isinstance(curso_nome, str):
                curso_nome = f"Curso {cod_curso_str}"
            db.add(Curso(codigo=cod_curso_str, nome=curso_nome))
    db.commit()

    # 2. Reúne todos os códigos e seus nomes de disciplinas por curso
    # Mapeamento de (curso, codigo) -> nome_original
    disciplinas_info: Dict[Tuple[str, str], str] = {}
    
    # Do currículo
    for _, row in df_curriculo.iterrows():
        curso = str(row['cod_curso'])
        codigo = str(row['cod_disciplina'])
        nome = str(row['nome_disciplina'])
        disciplinas_info[(curso, codigo)] = nome
        
    # Do histórico
    col_hist_cod = 'cod_ativ_curric' if 'cod_ativ_curric' in df_historico.columns else 'disciplina_codigo'
    col_hist_nome = 'nome_ativ_curric' if 'nome_ativ_curric' in df_historico.columns else 'nome_disciplina'
    for _, row in df_historico.iterrows():
        curso = str(row['cod_curso'])
        codigo = str(row[col_hist_cod])
        nome = str(row[col_hist_nome])
        if (curso, codigo) not in disciplinas_info:
            disciplinas_info[(curso, codigo)] = nome

    # 3. Agrupamento por (curso, nome_normalizado)
    # conceito_id -> {"curso": curso, "nome_normalizado": nome_norm, "codigos": {codigos}}
    conceitos_grupos: Dict[str, Dict] = {}
    # (curso, codigo) -> conceito_id
    mapeamento_codigo_conceito: Dict[Tuple[str, str], str] = {}

    for (curso, codigo), nome_original in disciplinas_info.items():
        nome_norm = normalizar_nome(nome_original)
        # Slug de conceito: ex. CC-CALCULO_I
        slug_nome = nome_norm.replace(" ", "_")
        conceito_id = f"{curso}-{slug_nome}"
        
        if conceito_id not in conceitos_grupos:
            conceitos_grupos[conceito_id] = {
                "curso": curso,
                "nome_normalizado": nome_norm,
                "codigos": set()
            }
        
        conceitos_grupos[conceito_id]["codigos"].add(codigo)
        mapeamento_codigo_conceito[(curso, codigo)] = conceito_id

    # 4. Trata equivalências diretas do currículo para fundir conceitos se necessário
    if 'equivalencias' in df_curriculo.columns:
        for _, row in df_curriculo.iterrows():
            curso = str(row['cod_curso'])
            codigo = str(row['cod_disciplina'])
            equivs_str = row['equivalencias']
            
            if pd.isna(equivs_str) or not isinstance(equivs_str, str):
                continue
                
            # Equivalências vêm separadas por vírgula no CSV
            codigos_equiv = [c.strip() for c in equivs_str.split(",") if c.strip()]
            
            conceito_id_atual = mapeamento_codigo_conceito.get((curso, codigo))
            if not conceito_id_atual:
                continue
                
            for cod_eq in codigos_equiv:
                # Se o código equivalente está mapeado em outro conceito
                conceito_id_eq = mapeamento_codigo_conceito.get((curso, cod_eq))
                if conceito_id_eq and conceito_id_eq != conceito_id_atual:
                    # Funde o conceito_id_eq no conceito_id_atual
                    grupo_eq = conceitos_grupos.pop(conceito_id_eq)
                    for c_codigo in grupo_eq["codigos"]:
                        conceitos_grupos[conceito_id_atual]["codigos"].add(c_codigo)
                        mapeamento_codigo_conceito[(curso, c_codigo)] = conceito_id_atual

    # 5. Salva os conceitos no banco
    for c_id, grupo in conceitos_grupos.items():
        # Verifica se já existe
        c_existente = db.query(ConceitoDisciplina).filter(ConceitoDisciplina.id == c_id).first()
        if not c_existente:
            c_novo = ConceitoDisciplina(
                id=c_id,
                curso_codigo=grupo["curso"],
                nome_normalizado=grupo["nome_normalizado"]
            )
            db.add(c_novo)
            
    db.commit()

    # 6. Salva os códigos brutos de tradução no banco
    for (curso, codigo), c_id in mapeamento_codigo_conceito.items():
        # Busca se há versão do PPC e situação curriculo do df_curriculo
        match = df_curriculo[(df_curriculo['cod_curso'] == curso) & (df_curriculo['cod_disciplina'] == codigo)]
        versao = None
        situacao = "CORRENTE"
        
        if not match.empty:
            col_versao = 'num_versao' if 'num_versao' in match.columns else ('versao' if 'versao' in match.columns else None)
            if col_versao:
                versao = int(pd.to_numeric(match.iloc[0][col_versao], errors='coerce') or 2023)
            situacao = str(match.iloc[0]['situacao']) if 'situacao' in match.columns else "CORRENTE"

        cod_existente = db.query(CodigoDisciplina).filter(
            CodigoDisciplina.codigo == codigo,
            CodigoDisciplina.curso_codigo == curso
        ).first()
        
        if not cod_existente:
            cod_novo = CodigoDisciplina(
                codigo=codigo,
                curso_codigo=curso,
                conceito_id=c_id,
                versao_ppc_origem=versao,
                situacao_curriculo=situacao
            )
            db.add(cod_novo)
        else:
            cod_existente.conceito_id = c_id
            if versao:
                cod_existente.versao_ppc_origem = versao
            cod_existente.situacao_curriculo = situacao

    db.commit()
    return mapeamento_codigo_conceito


def montar_vinculos_curriculares(db: Session, df_curriculo: pd.DataFrame, conceitos: Dict[Tuple[str, str], str]):
    """Cria os registros de VinculoCurricular para as disciplinas da grade."""
    vinculos_a_criar = {}
    for _, row in df_curriculo.iterrows():
        curso = str(row['cod_curso'])
        codigo = str(row['cod_disciplina'])
        c_id = conceitos.get((curso, codigo))
        if not c_id:
            continue
        periodo_ideal = row['periodo_ideal']
        p_ideal = int(periodo_ideal) if pd.notna(periodo_ideal) else None
        
        chave = (curso, c_id)
        if chave not in vinculos_a_criar:
            vinculos_a_criar[chave] = p_ideal
        else:
            if p_ideal is not None and (vinculos_a_criar[chave] is None or p_ideal < vinculos_a_criar[chave]):
                vinculos_a_criar[chave] = p_ideal

    for (curso, c_id), p_ideal in vinculos_a_criar.items():
        vinc_existente = db.query(VinculoCurricular).filter(
            VinculoCurricular.curso_codigo == curso,
            VinculoCurricular.conceito_id == c_id
        ).first()
        
        if not vinc_existente:
            vinc_novo = VinculoCurricular(
                curso_codigo=curso,
                conceito_id=c_id,
                periodo_sugerido=p_ideal,
                periodicidade_oferta=None
            )
            db.add(vinc_novo)
        else:
            if p_ideal is not None:
                vinc_existente.periodo_sugerido = p_ideal
                
    db.commit()


def montar_pre_requisitos(db: Session, df_curriculo: pd.DataFrame, conceitos: Dict[Tuple[str, str], str]):
    """Mapeia os pré-requisitos citados no currículo para seus conceitos no banco."""
    if 'pre_requisitos' not in df_curriculo.columns:
        return
        
    prereqs_a_criar = set()
    for _, row in df_curriculo.iterrows():
        curso = str(row['cod_curso'])
        codigo = str(row['cod_disciplina'])
        c_id = conceitos.get((curso, codigo))
        
        if not c_id:
            continue
            
        prereqs_str = row['pre_requisitos']
        if pd.isna(prereqs_str) or not isinstance(prereqs_str, str):
            continue
            
        linhas_prereq = [p.strip() for p in prereqs_str.split(",") if p.strip()]
        for p_str in linhas_prereq:
            p_cod = p_str.split("-")[0].strip()
            p_conceito_id = conceitos.get((curso, p_cod))
            
            if not p_conceito_id:
                msg = f"Aviso: Pré-requisito '{p_str}' da disciplina {codigo} (curso {curso}) não foi encontrado na base de conceitos."
                EXCECOES.append(msg)
                continue
                
            prereqs_a_criar.add((curso, c_id, p_conceito_id))
            
    for curso, c_id, p_conceito_id in prereqs_a_criar:
        prereq_existente = db.query(PreRequisito).filter(
            PreRequisito.curso_codigo == curso,
            PreRequisito.conceito_id == c_id,
            PreRequisito.conceito_prerequisito_id == p_conceito_id
        ).first()
        
        if not prereq_existente:
            prereq_novo = PreRequisito(
                curso_codigo=curso,
                conceito_id=c_id,
                conceito_prerequisito_id=p_conceito_id,
                grupo_alternativo=None
            )
            db.add(prereq_novo)
            
    db.commit()


def relatorio_excecoes() -> List[str]:
    """Retorna as inconsistências identificadas durante a execução do ETL."""
    return EXCECOES
