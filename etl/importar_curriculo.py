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
    col_map = {}
    for col in df.columns:
        c = unicodedata.normalize('NFKD', str(col).lower().strip()).encode('ASCII', 'ignore').decode('ASCII')
        c = re.sub(r'[^a-z0-9_]', '_', c).strip('_')

        if c == 'cod_curso' or (c.startswith('cod') and 'curso' in c):
            col_map[col] = 'cod_curso'
        elif c == 'curso' or c == 'nome_curso':
            col_map[col] = 'curso'
        elif c in ('cod_disciplina', 'cod_ativ_curric', 'cod_ativ') or (c.startswith('cod') and ('disc' in c or 'ativ' in c)):
            col_map[col] = 'cod_disciplina'
        elif c in ('nome_disciplina', 'nome_ativ_curric', 'disciplina') or (c.startswith('nome') and ('disc' in c or 'ativ' in c)):
            col_map[col] = 'nome_disciplina'
        elif 'tipo' in c and 'disc' in c:
            col_map[col] = 'tipo_disciplina'
        elif c == 'periodo_ideal':
            col_map[col] = 'periodo_ideal'
        elif c == 'semestre_ideal' and 'periodo_ideal' not in df.columns:
            col_map[col] = 'periodo_ideal'
        elif 'req' in c:
            col_map[col] = 'pre_requisitos'
        elif 'equiv' in c:
            col_map[col] = 'equivalencias'
        elif c == 'situacao' or (c.startswith('situ') and 'disc' not in c and 'mat' not in c):
            col_map[col] = 'situacao'
        elif c == 'num_versao':
            col_map[col] = 'num_versao'
        elif c == 'versao':
            col_map[col] = 'versao'
        else:
            col_map[col] = col

    return df.rename(columns=col_map)


def ler_csv_curriculo(caminho: str) -> pd.DataFrame:
    """Abre o CSV com separador ';' e encoding 'utf-8' ou 'latin-1'."""
    try:
        df = pd.read_csv(caminho, sep=';', encoding='utf-8')
    except (UnicodeDecodeError, ValueError):
        df = pd.read_csv(caminho, sep=';', encoding='latin-1')
    return normalizar_colunas(df)


def deduplicar_versoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mantém apenas a versão ativa/corrente mais recente de cada disciplina por curso.
    Prioriza a versão marcada como 'CORRENTE', depois 'ATIVO', e a versão mais recente.
    """
    if df.empty:
        return df

    # Filtra apenas registros ativos se a coluna 'situacao' existir
    if 'situacao' in df.columns:
        mask_ativa = df['situacao'].astype(str).str.upper().str.contains('ATIVA')
        df_ativos = df[mask_ativa].copy()
        if df_ativos.empty:
            df_ativos = df.copy()
    else:
        df_ativos = df.copy()

    # Prioriza versao == 'CORRENTE' (peso 2), depois 'ATIVO' (peso 1)
    if 'versao' in df_ativos.columns:
        df_ativos['_peso_versao'] = df_ativos['versao'].astype(str).str.upper().map({
            'CORRENTE': 2,
            'ATIVO': 1
        }).fillna(0)
    else:
        df_ativos['_peso_versao'] = 0

    # Extrai ano numérico da coluna num_versao (ex: '2023', '2014T' -> 2014)
    col_num_versao = 'num_versao' if 'num_versao' in df_ativos.columns else None
    if col_num_versao:
        df_ativos['_ano_versao'] = df_ativos[col_num_versao].astype(str).str.extract(r'(\d+)')[0]
        df_ativos['_ano_versao'] = pd.to_numeric(df_ativos['_ano_versao'], errors='coerce').fillna(0)
    else:
        df_ativos['_ano_versao'] = 0

    df_ativos = df_ativos.sort_values(by=['_peso_versao', '_ano_versao'], ascending=[False, False])
    df_dedup = df_ativos.drop_duplicates(subset=['cod_curso', 'cod_disciplina'], keep='first').copy()
    df_dedup = df_dedup.drop(columns=['_peso_versao', '_ano_versao'], errors='ignore')
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
    conceitos_existentes = set(r[0] for r in db.query(ConceitoDisciplina.id).all())
    novos_conceitos = []
    for c_id, grupo in conceitos_grupos.items():
        if c_id not in conceitos_existentes:
            novos_conceitos.append(ConceitoDisciplina(
                id=c_id,
                curso_codigo=grupo["curso"],
                nome_normalizado=grupo["nome_normalizado"]
            ))
            conceitos_existentes.add(c_id)
            
    if novos_conceitos:
        db.bulk_save_objects(novos_conceitos)
    db.commit()

    # 6. Salva os códigos brutos de tradução no banco
    cods_existentes = set((r[0], r[1]) for r in db.query(CodigoDisciplina.codigo, CodigoDisciplina.curso_codigo).all())
    novos_codigos = []
    for (curso, codigo), c_id in mapeamento_codigo_conceito.items():
        match = df_curriculo[(df_curriculo['cod_curso'] == curso) & (df_curriculo['cod_disciplina'] == codigo)]
        versao = None
        situacao = "CORRENTE"
        
        if not match.empty:
            col_versao = 'num_versao' if 'num_versao' in match.columns else ('versao' if 'versao' in match.columns else None)
            if col_versao:
                v_str = str(match.iloc[0][col_versao])
                num_match = re.search(r'\d+', v_str)
                versao = int(num_match.group(0)) if num_match else 2023
            situacao = str(match.iloc[0]['situacao']) if 'situacao' in match.columns else "CORRENTE"

        if (codigo, curso) not in cods_existentes:
            novos_codigos.append(CodigoDisciplina(
                codigo=codigo,
                curso_codigo=curso,
                conceito_id=c_id,
                versao_ppc_origem=versao,
                situacao_curriculo=situacao
            ))
            cods_existentes.add((codigo, curso))

    if novos_codigos:
        db.bulk_save_objects(novos_codigos)
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
        try:
            p_ideal = int(float(periodo_ideal)) if pd.notna(periodo_ideal) else None
        except (ValueError, TypeError):
            p_ideal = None
        
        chave = (curso, c_id)
        if chave not in vinculos_a_criar:
            vinculos_a_criar[chave] = p_ideal
        else:
            if p_ideal is not None and (vinculos_a_criar[chave] is None or p_ideal < vinculos_a_criar[chave]):
                vinculos_a_criar[chave] = p_ideal

    vinculos_existentes = set((r[0], r[1]) for r in db.query(VinculoCurricular.curso_codigo, VinculoCurricular.conceito_id).all())
    novos_vinculos = []
    for (curso, c_id), p_ideal in vinculos_a_criar.items():
        if (curso, c_id) not in vinculos_existentes:
            novos_vinculos.append(VinculoCurricular(
                curso_codigo=curso,
                conceito_id=c_id,
                periodo_sugerido=p_ideal,
                periodicidade_oferta=None
            ))
            vinculos_existentes.add((curso, c_id))

    if novos_vinculos:
        db.bulk_save_objects(novos_vinculos)
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
            
    prereqs_existentes = set((r[0], r[1], r[2]) for r in db.query(
        PreRequisito.curso_codigo, PreRequisito.conceito_id, PreRequisito.conceito_prerequisito_id
    ).all())
    novos_prereqs = []
    for curso, c_id, p_conceito_id in prereqs_a_criar:
        if (curso, c_id, p_conceito_id) not in prereqs_existentes:
            novos_prereqs.append(PreRequisito(
                curso_codigo=curso,
                conceito_id=c_id,
                conceito_prerequisito_id=p_conceito_id,
                grupo_alternativo=None
            ))
            prereqs_existentes.add((curso, c_id, p_conceito_id))
            
    if novos_prereqs:
        db.bulk_save_objects(novos_prereqs)
    db.commit()


def relatorio_excecoes() -> List[str]:
    """Retorna as inconsistências identificadas durante a execução do ETL."""
    return EXCECOES
