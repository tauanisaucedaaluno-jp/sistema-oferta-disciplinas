"""
Script para popular o banco de dados com dados fictícios de teste (seeding).

Este script cria um conjunto representativo de dados de cursos, conceitos de
disciplina, códigos brutos, pré-requisitos, vínculos curriculares, alunos,
histórico de matrículas e usuários para permitir testar o motor de regras
(cálculo de demanda) e a API antes de receber os CSVs reais da UNIPAMPA.

Cursos incluídos:
  - CC  — Ciência da Computação
  - ES  — Engenharia de Software
  - EC  — Engenharia Civil

Disciplinas compartilhadas entre cursos (para testar RF12):
  - CALCULO I   → CC, ES, EC
  - CALCULO II  → CC, ES, EC
  - FISICA I    → CC (ímpar), EC (ímpar)
  - ALGEBRA LINEAR → CC (ímpar), ES (par — extraordinária em ímpar)

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

    # =========================================================================
    # 1. CURSOS
    # =========================================================================
    cursos = [
        Curso(codigo="CC", nome="Ciência da Computação"),
        Curso(codigo="ES", nome="Engenharia de Software"),
        Curso(codigo="EC", nome="Engenharia Civil"),
    ]
    db.add_all(cursos)
    db.commit()

    # =========================================================================
    # 2. CONCEITOS DE DISCIPLINA
    # Cada curso tem seu próprio conceito (ADR 0003 / RN01).
    # Disciplinas com mesmo nome_normalizado em cursos diferentes são
    # "compartilhadas" para fins de RF12.
    # =========================================================================
    conceitos = [
        # --- Ciência da Computação ---
        ConceitoDisciplina(id="CC-CALC1",   curso_codigo="CC", nome_normalizado="CALCULO I"),
        ConceitoDisciplina(id="CC-CALC2",   curso_codigo="CC", nome_normalizado="CALCULO II"),
        ConceitoDisciplina(id="CC-CALC3",   curso_codigo="CC", nome_normalizado="CALCULO III"),
        ConceitoDisciplina(id="CC-PROG1",   curso_codigo="CC", nome_normalizado="PROGRAMACAO I"),
        ConceitoDisciplina(id="CC-PROG2",   curso_codigo="CC", nome_normalizado="PROGRAMACAO II"),
        ConceitoDisciplina(id="CC-ALG",     curso_codigo="CC", nome_normalizado="ALGEBRA LINEAR"),
        ConceitoDisciplina(id="CC-FIS1",    curso_codigo="CC", nome_normalizado="FISICA I"),

        # --- Engenharia de Software ---
        ConceitoDisciplina(id="ES-CALC1",   curso_codigo="ES", nome_normalizado="CALCULO I"),
        ConceitoDisciplina(id="ES-CALC2",   curso_codigo="ES", nome_normalizado="CALCULO II"),
        ConceitoDisciplina(id="ES-PROG1",   curso_codigo="ES", nome_normalizado="PROGRAMACAO I"),
        ConceitoDisciplina(id="ES-ALG",     curso_codigo="ES", nome_normalizado="ALGEBRA LINEAR"),
        ConceitoDisciplina(id="ES-ENG",     curso_codigo="ES", nome_normalizado="ENGENHARIA DE SOFTWARE"),

        # --- Engenharia Civil ---
        ConceitoDisciplina(id="EC-CALC1",   curso_codigo="EC", nome_normalizado="CALCULO I"),
        ConceitoDisciplina(id="EC-CALC2",   curso_codigo="EC", nome_normalizado="CALCULO II"),
        ConceitoDisciplina(id="EC-FIS1",    curso_codigo="EC", nome_normalizado="FISICA I"),
        ConceitoDisciplina(id="EC-RESIST",  curso_codigo="EC", nome_normalizado="RESISTENCIA DOS MATERIAIS"),
        ConceitoDisciplina(id="EC-ESTRU",   curso_codigo="EC", nome_normalizado="ESTRUTURAS I"),
    ]
    db.add_all(conceitos)
    db.commit()

    # =========================================================================
    # 3. CÓDIGOS DE DISCIPLINA
    # =========================================================================
    codigos = [
        # CC — Cálculo I (dois códigos históricos)
        CodigoDisciplina(codigo="AL0001", curso_codigo="CC", conceito_id="CC-CALC1", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0363", curso_codigo="CC", conceito_id="CC-CALC1", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # CC — Cálculo II
        CodigoDisciplina(codigo="AL0002", curso_codigo="CC", conceito_id="CC-CALC2", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0364", curso_codigo="CC", conceito_id="CC-CALC2", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # CC — Cálculo III
        CodigoDisciplina(codigo="AL0003", curso_codigo="CC", conceito_id="CC-CALC3", versao_ppc_origem=2018, situacao_curriculo="INATIVO"),
        CodigoDisciplina(codigo="AL0365", curso_codigo="CC", conceito_id="CC-CALC3", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # CC — Programação I / II
        CodigoDisciplina(codigo="AL0101", curso_codigo="CC", conceito_id="CC-PROG1", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        CodigoDisciplina(codigo="AL0102", curso_codigo="CC", conceito_id="CC-PROG2", versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # CC — Álgebra Linear
        CodigoDisciplina(codigo="AL0201", curso_codigo="CC", conceito_id="CC-ALG",   versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),
        # CC — Física I
        CodigoDisciplina(codigo="AL0301", curso_codigo="CC", conceito_id="CC-FIS1",  versao_ppc_origem=2023, situacao_curriculo="CORRENTE"),

        # ES — Cálculo I / II
        CodigoDisciplina(codigo="ES0001", curso_codigo="ES", conceito_id="ES-CALC1", versao_ppc_origem=2021, situacao_curriculo="CORRENTE"),
        CodigoDisciplina(codigo="ES0002", curso_codigo="ES", conceito_id="ES-CALC2", versao_ppc_origem=2021, situacao_curriculo="CORRENTE"),
        # ES — Programação I
        CodigoDisciplina(codigo="ES0101", curso_codigo="ES", conceito_id="ES-PROG1", versao_ppc_origem=2021, situacao_curriculo="CORRENTE"),
        # ES — Álgebra Linear
        CodigoDisciplina(codigo="ES0201", curso_codigo="ES", conceito_id="ES-ALG",   versao_ppc_origem=2021, situacao_curriculo="CORRENTE"),
        # ES — Engenharia de Software
        CodigoDisciplina(codigo="ES0301", curso_codigo="ES", conceito_id="ES-ENG",   versao_ppc_origem=2021, situacao_curriculo="CORRENTE"),

        # EC — Cálculo I / II
        CodigoDisciplina(codigo="EC0001", curso_codigo="EC", conceito_id="EC-CALC1", versao_ppc_origem=2020, situacao_curriculo="CORRENTE"),
        CodigoDisciplina(codigo="EC0002", curso_codigo="EC", conceito_id="EC-CALC2", versao_ppc_origem=2020, situacao_curriculo="CORRENTE"),
        # EC — Física I
        CodigoDisciplina(codigo="EC0101", curso_codigo="EC", conceito_id="EC-FIS1",  versao_ppc_origem=2020, situacao_curriculo="CORRENTE"),
        # EC — Resistência dos Materiais / Estruturas I
        CodigoDisciplina(codigo="EC0201", curso_codigo="EC", conceito_id="EC-RESIST",versao_ppc_origem=2020, situacao_curriculo="CORRENTE"),
        CodigoDisciplina(codigo="EC0202", curso_codigo="EC", conceito_id="EC-ESTRU", versao_ppc_origem=2020, situacao_curriculo="CORRENTE"),
    ]
    db.add_all(codigos)
    db.commit()

    # =========================================================================
    # 4. VÍNCULOS CURRICULARES
    # Periodicidades variadas para testar TODOS os cenários de oferta:
    #   - impar: aparece em modo extraordinário quando semestre selecionado é PAR
    #   - par:   aparece em modo extraordinário quando semestre selecionado é ÍMPAR
    #   - ambos: nunca aparece em modo extraordinário
    # =========================================================================
    vinculos = [
        # --- CC ---
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC1", periodicidade_oferta="impar", periodo_sugerido=1),
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC2", periodicidade_oferta="par",   periodo_sugerido=2),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC3", periodicidade_oferta="impar", periodo_sugerido=3),
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-PROG1", periodicidade_oferta="impar", periodo_sugerido=1),
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-PROG2", periodicidade_oferta="par",   periodo_sugerido=2),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-ALG",   periodicidade_oferta="par",   periodo_sugerido=2),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="CC", conceito_id="CC-FIS1",  periodicidade_oferta="impar", periodo_sugerido=3),

        # --- ES ---
        VinculoCurricular(curso_codigo="ES", conceito_id="ES-CALC1", periodicidade_oferta="impar", periodo_sugerido=1),
        VinculoCurricular(curso_codigo="ES", conceito_id="ES-CALC2", periodicidade_oferta="par",   periodo_sugerido=2),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="ES", conceito_id="ES-PROG1", periodicidade_oferta="impar", periodo_sugerido=1),
        VinculoCurricular(curso_codigo="ES", conceito_id="ES-ALG",   periodicidade_oferta="par",   periodo_sugerido=4),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="ES", conceito_id="ES-ENG",   periodicidade_oferta="impar", periodo_sugerido=3),

        # --- EC ---
        VinculoCurricular(curso_codigo="EC", conceito_id="EC-CALC1", periodicidade_oferta="impar", periodo_sugerido=1),
        VinculoCurricular(curso_codigo="EC", conceito_id="EC-CALC2", periodicidade_oferta="par",   periodo_sugerido=2),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="EC", conceito_id="EC-FIS1",  periodicidade_oferta="impar", periodo_sugerido=3),
        VinculoCurricular(curso_codigo="EC", conceito_id="EC-RESIST",periodicidade_oferta="par",   periodo_sugerido=5),  # extraord. em ímpar
        VinculoCurricular(curso_codigo="EC", conceito_id="EC-ESTRU", periodicidade_oferta="impar", periodo_sugerido=6),
    ]
    db.add_all(vinculos)
    db.commit()

    # =========================================================================
    # 5. PRÉ-REQUISITOS
    # =========================================================================
    prereqs = [
        # CC
        PreRequisito(curso_codigo="CC", conceito_id="CC-CALC2", conceito_prerequisito_id="CC-CALC1"),
        PreRequisito(curso_codigo="CC", conceito_id="CC-CALC3", conceito_prerequisito_id="CC-CALC2"),
        PreRequisito(curso_codigo="CC", conceito_id="CC-PROG2", conceito_prerequisito_id="CC-PROG1"),
        PreRequisito(curso_codigo="CC", conceito_id="CC-ALG",   conceito_prerequisito_id="CC-CALC1"),

        # ES
        PreRequisito(curso_codigo="ES", conceito_id="ES-CALC2", conceito_prerequisito_id="ES-CALC1"),
        PreRequisito(curso_codigo="ES", conceito_id="ES-ALG",   conceito_prerequisito_id="ES-CALC1"),

        # EC
        PreRequisito(curso_codigo="EC", conceito_id="EC-CALC2", conceito_prerequisito_id="EC-CALC1"),
        PreRequisito(curso_codigo="EC", conceito_id="EC-RESIST",conceito_prerequisito_id="EC-CALC2"),
        PreRequisito(curso_codigo="EC", conceito_id="EC-ESTRU", conceito_prerequisito_id="EC-RESIST"),
    ]
    db.add_all(prereqs)
    db.commit()

    # =========================================================================
    # 6. USUÁRIOS (RF13, RNF01)
    # =========================================================================
    usuarios = [
        Usuario(email="coordenador@unipampa.edu.br", senha_hash=hash_password("coordenador123"), papel="coordenador", ativo=True),
        Usuario(email="admin@unipampa.edu.br",        senha_hash=hash_password("admin123"),        papel="admin",        ativo=True),
    ]
    db.add_all(usuarios)
    db.commit()

    # =========================================================================
    # 7. ALUNOS
    # =========================================================================
    alunos = [
        # CC
        Aluno(matricula="18CC001", curso_codigo="CC", semestre_ingresso="2018/1"),
        Aluno(matricula="23CC002", curso_codigo="CC", semestre_ingresso="2023/1"),
        Aluno(matricula="24CC003", curso_codigo="CC", semestre_ingresso="2024/1"),
        Aluno(matricula="24CC004", curso_codigo="CC", semestre_ingresso="2024/1"),
        Aluno(matricula="24CC005", curso_codigo="CC", semestre_ingresso="2024/1"),
        Aluno(matricula="24CC006", curso_codigo="CC", semestre_ingresso="2024/1"),
        # ES
        Aluno(matricula="22ES001", curso_codigo="ES", semestre_ingresso="2022/1"),
        Aluno(matricula="23ES002", curso_codigo="ES", semestre_ingresso="2023/1"),
        Aluno(matricula="24ES003", curso_codigo="ES", semestre_ingresso="2024/1"),
        Aluno(matricula="24ES004", curso_codigo="ES", semestre_ingresso="2024/1"),
        # EC
        Aluno(matricula="21EC001", curso_codigo="EC", semestre_ingresso="2021/1"),
        Aluno(matricula="22EC002", curso_codigo="EC", semestre_ingresso="2022/1"),
        Aluno(matricula="24EC003", curso_codigo="EC", semestre_ingresso="2024/1"),
        Aluno(matricula="24EC004", curso_codigo="EC", semestre_ingresso="2024/1"),
        Aluno(matricula="24EC005", curso_codigo="EC", semestre_ingresso="2024/1"),
    ]
    db.add_all(alunos)
    db.commit()

    # =========================================================================
    # 8. HISTÓRICO ESCOLAR
    # Cenários testados:
    #   - Grupo A: aluno cursando a disciplina agora (2026/1)
    #   - Grupo B: aluno aprovado em todos pré-requisitos, nunca cursou o alvo
    #   - Grupo C: aluno cursando um pré-requisito agora (2026/1)
    #   - Evasão: aluno com Abandono — deve ser excluído de B e C (RN05)
    #   - Disciplinas compartilhadas: CC e ES têm CALCULO I, CALCULO II e
    #     ALGEBRA LINEAR em comum (mesmo nome_normalizado) — testa RF12
    # =========================================================================
    historicos = [
        # ---- CC — Aluno 18CC001: veterano, passou em tudo ----
        Historico(aluno_matricula="18CC001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2018/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="18CC001", curso_codigo="CC", disciplina_codigo="AL0002", periodo_letivo="2018/2", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="18CC001", curso_codigo="CC", disciplina_codigo="AL0003", periodo_letivo="2019/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="18CC001", curso_codigo="CC", disciplina_codigo="AL0101", periodo_letivo="2018/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),

        # ---- CC — Aluno 23CC002: aprovado em Calc I, cursando Calc II em 2026/1 (Grupo A para CALC2) ----
        Historico(aluno_matricula="23CC002", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2023/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="23CC002", curso_codigo="CC", disciplina_codigo="AL0364", periodo_letivo="2023/2", situacao="reprovado", situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="23CC002", curso_codigo="CC", disciplina_codigo="AL0364", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- CC — Aluno 24CC003: cursando Calc I em 2026/1 (Grupo A para CALC1, Grupo C para CALC2 via pré-req) ----
        Historico(aluno_matricula="24CC003", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- CC — Aluno 24CC004: reprovado em Calc I, evadiu (deve ser excluído de B e C — RN05) ----
        Historico(aluno_matricula="24CC004", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2024/1", situacao="reprovado", situacao_matricula="Abandono"),

        # ---- CC — Aluno 24CC005: aprovado em Calc I e Prog I; apto para Calc II (Grupo B) e Alg Linear (Grupo B) ----
        Historico(aluno_matricula="24CC005", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2024/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="24CC005", curso_codigo="CC", disciplina_codigo="AL0101", periodo_letivo="2024/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),

        # ---- CC — Aluno 24CC006: cursando Calc I em 2026/1 (Grupo C para Calc II e Alg Linear) ----
        Historico(aluno_matricula="24CC006", curso_codigo="CC", disciplina_codigo="AL0363", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- ES — Aluno 22ES001: aprovado em Calc I de ES; apto para Calc II e Alg (Grupo B) ----
        Historico(aluno_matricula="22ES001", curso_codigo="ES", disciplina_codigo="ES0001", periodo_letivo="2022/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),

        # ---- ES — Aluno 23ES002: aprovado em Calc I; cursando Calc II em 2026/1 (Grupo A para ES-CALC2) ----
        Historico(aluno_matricula="23ES002", curso_codigo="ES", disciplina_codigo="ES0001", periodo_letivo="2023/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="23ES002", curso_codigo="ES", disciplina_codigo="ES0002", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- ES — Aluno 24ES003: cursando Calc I em 2026/1 (Grupo A para ES-CALC1; Grupo C para ES-CALC2) ----
        Historico(aluno_matricula="24ES003", curso_codigo="ES", disciplina_codigo="ES0001", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- ES — Aluno 24ES004: nunca cursou nada; não entra em nenhum grupo (sem pré-req cumprido) ----

        # ---- EC — Aluno 21EC001: veterano, passou em Calc I e II ----
        Historico(aluno_matricula="21EC001", curso_codigo="EC", disciplina_codigo="EC0001", periodo_letivo="2021/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),
        Historico(aluno_matricula="21EC001", curso_codigo="EC", disciplina_codigo="EC0002", periodo_letivo="2021/2", situacao="aprovado",  situacao_matricula="Aluno Regular"),

        # ---- EC — Aluno 22EC002: aprovado em Calc I; apto para Calc II (Grupo B) ----
        Historico(aluno_matricula="22EC002", curso_codigo="EC", disciplina_codigo="EC0001", periodo_letivo="2022/1", situacao="aprovado",  situacao_matricula="Aluno Regular"),

        # ---- EC — Aluno 24EC003: cursando Calc I em 2026/1 (Grupo A para EC-CALC1; Grupo C para EC-CALC2) ----
        Historico(aluno_matricula="24EC003", curso_codigo="EC", disciplina_codigo="EC0001", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- EC — Aluno 24EC004: cursando Calc I em 2026/1 ----
        Historico(aluno_matricula="24EC004", curso_codigo="EC", disciplina_codigo="EC0001", periodo_letivo="2026/1", situacao="cursando",  situacao_matricula="Aluno Regular"),

        # ---- EC — Aluno 24EC005: nunca cursou nada ----
    ]
    db.add_all(historicos)
    db.commit()

    print("=" * 60)
    print("Populacao do banco concluida com sucesso!")
    print()
    print("Cursos criados: CC, ES, EC")
    print("Disciplinas compartilhadas (testam RF12):")
    print("  CALCULO I       -> CC, ES, EC")
    print("  CALCULO II      -> CC, ES, EC (par -> extraord. em impar)")
    print("  ALGEBRA LINEAR  -> CC, ES    (par -> extraord. em impar)")
    print("  FISICA I        -> CC, EC")
    print()
    print("Modo extraordinario (semestre impar, ex.: 2026/1):")
    print("  -> Mostra: CALCULO II, PROG II, ALGEBRA LINEAR, RESISTENCIA DOS MATERIAIS")
    print("Modo extraordinario (semestre par, ex.: 2024/2):")
    print("  -> Mostra: CALCULO I, CALCULO III, PROG I, FISICA I, ENG. DE SOFTWARE, ESTRUTURAS I")
    print("=" * 60)


def main():
    db = SessionLocal()
    try:
        clean_database(db)
        seed_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
