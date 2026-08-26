"""
Script para popular o banco de dados com dados fictícios de teste (seeding).

Este script cria um conjunto representativo de dados de cursos, conceitos de
disciplina, códigos brutos, pré-requisitos, vínculos curriculares, alunos,
histórico de matrículas e usuários para permitir testar o motor de regras
(cálculo de demanda) e a API antes de receber os CSVs reais da UNIPAMPA.

Pode ser executado com (dentro da raiz do projeto):
    python scripts/seed_db.py
"""

import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório src/backend ao sys.path e carrega as variáveis de ambiente do .env
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/backend"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.orm import Session
from db.database import SessionLocal, engine
from db.models import (
    Curso,
    ConceitoDisciplina,
    CodigoDisciplina,
    VinculoCurricular,
    PreRequisito,
    Aluno,
    Historico,
    Usuario,
    LogAcesso,
)

import bcrypt

def hash_password(password: str) -> str:
    """Gera o hash seguro para a senha informada utilizando a biblioteca bcrypt nativa (RNF01)."""
    # O bcrypt espera dados em bytes
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def clean_database(db: Session):
    """Limpa todos os dados existentes nas tabelas na ordem correta de chaves estrangeiras."""
    print("Limpando banco de dados...")
    db.query(LogAcesso).delete()
    db.query(Usuario).delete()
    db.query(PreRequisito).delete()
    db.query(VinculoCurricular).delete()
    db.query(CodigoDisciplina).delete()
    db.query(ConceitoDisciplina).delete()
    db.query(Historico).delete()
    db.query(Aluno).delete()
    db.query(Curso).delete()
    db.commit()


def seed_data(db: Session):
    """Cria os registros sintéticos no banco de dados."""
    print("Semeando dados fictícios...")

    # --- 1. CURSOS ---
    curso_cc = Curso(codigo="CC", nome="Ciência da Computação")
    db.add(curso_cc)
    db.commit()

    # --- 2. CONCEITOS DE DISCIPLINA (Identidades estáveis - ADR 0003) ---
    calc1 = ConceitoDisciplina(id="CC-CALC1", curso_codigo="CC", nome_normalizado="CALCULO I")
    calc2 = ConceitoDisciplina(id="CC-CALC2", curso_codigo="CC", nome_normalizado="CALCULO II")
    calc3 = ConceitoDisciplina(id="CC-CALC3", curso_codigo="CC", nome_normalizado="CALCULO III")
    prog1 = ConceitoDisciplina(id="CC-PROG1", curso_codigo="CC", nome_normalizado="PROGRAMACAO I")
    
    db.add_all([calc1, calc2, calc3, prog1])
    db.commit()

    # --- 3. CÓDIGOS DE DISCIPLINA (Variações reais de código - ADR 0003) ---
    codigos = [
        # Cálculo I
        CodigoDisciplina(codigo="AL0001", curso_codigo="CC", conceito_id="CC-CALC1", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0363", curso_codigo="CC", conceito_id="CC-CALC1", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # Cálculo II
        CodigoDisciplina(codigo="AL0002", curso_codigo="CC", conceito_id="CC-CALC2", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0364", curso_codigo="CC", conceito_id="CC-CALC2", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # Cálculo III
        CodigoDisciplina(codigo="AL0003", curso_codigo="CC", conceito_id="CC-CALC3", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0365", curso_codigo="CC", conceito_id="CC-CALC3", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # Programação I
        CodigoDisciplina(codigo="AL0101", curso_codigo="CC", conceito_id="CC-PROG1", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0102", curso_codigo="CC", conceito_id="CC-PROG1", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
    ]
    db.add_all(codigos)
    db.commit()

    # --- 4. VÍNCULOS CURRICULARES ---
    vinculos = [
        # Cálculo I é ofertado no primeiro semestre (ímpar)
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC1", periodicidade_oferta="impar", periodo_sugerido=1),
        # Cálculo II é ofertado no segundo semestre (par)
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC2", periodicidade_oferta="par", periodo_sugerido=2),
        # Cálculo III é ofertado no terceiro semestre (ímpar)
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC3", periodicidade_oferta="impar", periodo_sugerido=3),
        # Programação I é ofertado no primeiro semestre (ímpar)
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-PROG1", periodicidade_oferta="impar", periodo_sugerido=1),
    ]
    db.add_all(vinculos)
    db.commit()

    # --- 5. PRÉ-REQUISITOS ---
    prereqs = [
        # Cálculo II exige Cálculo I
        PreRequisito(curso_codigo="CC", conceito_id="CC-CALC2", conceito_prerequisito_id="CC-CALC1"),
        # Cálculo III exige Cálculo II
        PreRequisito(curso_codigo="CC", conceito_id="CC-CALC3", conceito_prerequisito_id="CC-CALC2"),
    ]
    db.add_all(prereqs)
    db.commit()

    # --- 6. USUÁRIOS (RF13, RNF01) ---
    usuarios = [
        Usuario(email="coordenador@unipampa.edu.br", senha_hash=hash_password("coordenador123"), papel="coordenador", ativo=True),
        Usuario(email="admin@unipampa.edu.br", senha_hash=hash_password("admin123"), papel="admin", ativo=True),
    ]
    db.add_all(usuarios)
    db.commit()

    # --- 7. ALUNOS ---
    alunos = [
        Aluno(matricula="18010001", curso_codigo="CC", semestre_ingresso="2018/1"),
        Aluno(matricula="23010002", curso_codigo="CC", semestre_ingresso="2023/1"),
        Aluno(matricula="24010003", curso_codigo="CC", semestre_ingresso="2024/1"),
        Aluno(matricula="24010004", curso_codigo="CC", semestre_ingresso="2024/1"),
        Aluno(matricula="24010005", curso_codigo="CC", semestre_ingresso="2024/1"),
    ]
    db.add_all(alunos)
    db.commit()

    # --- 8. HISTÓRICO ESCOLAR ---
    historicos = [
        # Aluno 1: Ingressou em 2018. Cursou e passou em tudo.
        Historico(aluno_matricula="18010001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2018/1", situacao="aprovado", situacao_matricula="Aluno Regular", nota=7.5),
        Historico(aluno_matricula="18010001", curso_codigo="CC", disciplina_codigo="AL0002", periodo_letivo="2018/2", situacao="aprovado", situacao_matricula="Aluno Regular", nota=6.0),
        Historico(aluno_matricula="18010001", curso_codigo="CC", disciplina_codigo="AL0003", periodo_letivo="2019/1", situacao="aprovado", situacao_matricula="Aluno Regular", nota=8.0),
        
        # Aluno 2: Aprovado em Calc I, reprovou no Calc II e está cursando Calc II novamente.
        Historico(aluno_matricula="23010002", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2023/1", situacao="aprovado", situacao_matricula="Aluno Regular", nota=8.5),
        Historico(aluno_matricula="23010002", curso_codigo="CC", disciplina_codigo="AL0364", periodo_letivo="2023/2", situacao="reprovado", situacao_matricula="Aluno Regular", nota=4.0),
        Historico(aluno_matricula="23010002", curso_codigo="CC", disciplina_codigo="AL0364", periodo_letivo="2024/1", situacao="cursando", situacao_matricula="Aluno Regular"),

        # Aluno 3: Cursando Cálculo I atualmente em 2024/1.
        Historico(aluno_matricula="24010003", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2024/1", situacao="cursando", situacao_matricula="Aluno Regular"),

        # Aluno 4: Reprovou em Cálculo I e evadiu (Abandono - deve ser ignorado em Grupo B/C pela RN05)
        Historico(aluno_matricula="24010004", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2024/1", situacao="reprovado", situacao_matricula="Abandono", nota=2.0),

        # Aluno 5: Aprovado em Cálculo I, está cursando Prog I em 2024/1.
        # Não tem histórico de Cálculo II, logo estará apto a cursá-lo em 2024/2 (Grupo B).
        Historico(aluno_matricula="24010005", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2024/1", situacao="aprovado", situacao_matricula="Aluno Regular", nota=9.0),
        Historico(aluno_matricula="24010005", curso_codigo="CC", disciplina_codigo="AL0102", periodo_letivo="2024/1", situacao="cursando", situacao_matricula="Aluno Regular"),
    ]
    db.add_all(historicos)
    db.commit()

    print("População do banco concluída com sucesso!")


def main():
    db = SessionLocal()
    try:
        clean_database(db)
        seed_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
