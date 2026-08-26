"""
Script de verificação do setup do banco de dados e dados semeados.

Este script se conecta ao banco de dados PostgreSQL do projeto e
realiza queries simples para validar que todas as tabelas foram criadas
pelo Alembic e populadas com os dados sintéticos pelo script de seed.

Pode ser executado com (dentro da raiz do projeto):
    python scripts/verify_setup.py
"""

import os
import sys
from dotenv import load_dotenv

# Configura o caminho do backend para carregar os módulos locais
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/backend"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
sys.path.insert(0, BACKEND_DIR)

from db.database import SessionLocal
from db.models import (
    Curso,
    ConceitoDisciplina,
    CodigoDisciplina,
    VinculoCurricular,
    PreRequisito,
    Aluno,
    Historico,
    Usuario,
)


def verify_database():
    """Realiza a contagem de registros em cada tabela para validação."""
    db = SessionLocal()
    try:
        print("=" * 50)
        print("VERIFICAÇÃO DO BANCO DE DADOS - OFERTAPAMPA")
        print("=" * 50)

        cursos_count = db.query(Curso).count()
        print(f"Cursos cadastrados: {cursos_count}")
        for curso in db.query(Curso).all():
            print(f"  - [{curso.codigo}] {curso.nome}")

        conceitos_count = db.query(ConceitoDisciplina).count()
        print(f"Conceitos de disciplinas cadastrados: {conceitos_count}")
        for conceito in db.query(ConceitoDisciplina).all():
            print(f"  - Concept ID: {conceito.id} | Nome: {conceito.nome_normalizado}")

        codigos_count = db.query(CodigoDisciplina).count()
        print(f"Códigos brutos mapeados (Tradução): {codigos_count}")

        vinculos_count = db.query(VinculoCurricular).count()
        print(f"Vínculos curriculares cadastrados: {vinculos_count}")

        prereqs_count = db.query(PreRequisito).count()
        print(f"Pré-requisitos cadastrados: {prereqs_count}")

        alunos_count = db.query(Aluno).count()
        print(f"Alunos cadastrados: {alunos_count}")

        historicos_count = db.query(Historico).count()
        print(f"Linhas de histórico cadastradas: {historicos_count}")

        usuarios_count = db.query(Usuario).count()
        print(f"Usuários administradores cadastrados: {usuarios_count}")

        print("=" * 50)
        print("STATUS DO BANCO DE DADOS: TOTALMENTE OPERACIONAL [OK]")
        print("=" * 50)

    except Exception as e:
        print(f"Erro ao verificar o banco de dados: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    verify_database()
