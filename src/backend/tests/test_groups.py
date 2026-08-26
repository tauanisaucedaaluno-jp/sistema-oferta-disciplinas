import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configura o path do backend para importar os módulos locais
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from db.database import Base
from db.models import Curso, ConceitoDisciplina, CodigoDisciplina, VinculoCurricular, PreRequisito, Aluno, Historico
from core.groups import grupo_a, grupo_b, grupo_c, demanda_estimada


@pytest.fixture(name="db")
def fixture_db():
    """Cria banco de dados SQLite em memória para testes isolados."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    
    # Adiciona Curso
    curso = Curso(codigo="CC", nome="Ciência da Computação")
    session.add(curso)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_grupo_a(db):
    # Setup: adiciona conceitos, códigos, alunos e históricos
    calc1 = ConceitoDisciplina(id="CC-CALC1", curso_codigo="CC", nome_normalizado="CALCULO I")
    db.add(calc1)
    db.commit()
    
    cod_calc1 = CodigoDisciplina(codigo="AL0001", curso_codigo="CC", conceito_id="CC-CALC1")
    db.add(cod_calc1)
    
    aluno1 = Aluno(matricula="1001", curso_codigo="CC")
    aluno2 = Aluno(matricula="1002", curso_codigo="CC")
    db.add_all([aluno1, aluno2])
    db.commit()
    
    # Aluno 1 está cursando em 2026/1
    hist1 = Historico(aluno_matricula="1001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2026/1", situacao="cursando")
    # Aluno 2 já foi aprovado em 2025/2
    hist2 = Historico(aluno_matricula="1002", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/2", situacao="aprovado")
    db.add_all([hist1, hist2])
    db.commit()
    
    # Execução
    resultado = grupo_a(db, "CC", "CC-CALC1", "2026/1")
    
    # Asserções
    assert "1001" in resultado
    assert "1002" not in resultado
    assert len(resultado) == 1


def test_grupo_b_requisito_simples(db):
    # Setup
    calc1 = ConceitoDisciplina(id="CC-CALC1", curso_codigo="CC", nome_normalizado="CALCULO I")
    calc2 = ConceitoDisciplina(id="CC-CALC2", curso_codigo="CC", nome_normalizado="CALCULO II")
    db.add_all([calc1, calc2])
    db.commit()
    
    cod_calc1 = CodigoDisciplina(codigo="AL0001", curso_codigo="CC", conceito_id="CC-CALC1")
    cod_calc2 = CodigoDisciplina(codigo="AL0002", curso_codigo="CC", conceito_id="CC-CALC2")
    db.add_all([cod_calc1, cod_calc2])
    
    # Cálculo II exige Cálculo I
    prereq = PreRequisito(curso_codigo="CC", conceito_id="CC-CALC2", conceito_prerequisito_id="CC-CALC1")
    db.add(prereq)
    
    # Vínculo curricular de Cálculo II
    vinc = VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC2", periodicidade_oferta="par", periodo_sugerido=2)
    db.add(vinc)
    
    # Aluno 1: passou no Cálculo I (Apto - Grupo B)
    aluno1 = Aluno(matricula="1001", curso_codigo="CC")
    hist1 = Historico(aluno_matricula="1001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/1", situacao="aprovado")
    
    # Aluno 2: não cursou Cálculo I (Não Apto)
    aluno2 = Aluno(matricula="1002", curso_codigo="CC")
    
    # Aluno 3: passou no Cálculo I, mas já está aprovado no Cálculo II (Não deve estar no Grupo B)
    aluno3 = Aluno(matricula="1003", curso_codigo="CC")
    hist3_1 = Historico(aluno_matricula="1003", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/1", situacao="aprovado")
    hist3_2 = Historico(aluno_matricula="1003", curso_codigo="CC", disciplina_codigo="AL0002", periodo_letivo="2025/2", situacao="aprovado")
    
    # Aluno 4: passou no Cálculo I, mas está cursando Cálculo II no período atual (Não deve estar no Grupo B)
    aluno4 = Aluno(matricula="1004", curso_codigo="CC")
    hist4_1 = Historico(aluno_matricula="1004", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/1", situacao="aprovado")
    hist4_2 = Historico(aluno_matricula="1004", curso_codigo="CC", disciplina_codigo="AL0002", periodo_letivo="2026/1", situacao="cursando")
    
    db.add_all([aluno1, aluno2, aluno3, aluno4])
    db.add_all([hist1, hist3_1, hist3_2, hist4_1, hist4_2])
    db.commit()
    
    # Execução
    resultado = grupo_b(db, "CC", "CC-CALC2")
    
    # Asserções
    assert "1001" in resultado
    assert "1002" not in resultado
    assert "1003" not in resultado
    assert "1004" not in resultado
    assert len(resultado) == 1


def test_grupo_b_requisitos_alternativos(db):
    # Setup: Física II exige (Física I-A OU Física I-B)
    fis1a = ConceitoDisciplina(id="CC-FIS1A", curso_codigo="CC", nome_normalizado="FISICA I A")
    fis1b = ConceitoDisciplina(id="CC-FIS1B", curso_codigo="CC", nome_normalizado="FISICA I B")
    fis2 = ConceitoDisciplina(id="CC-FIS2", curso_codigo="CC", nome_normalizado="FISICA II")
    db.add_all([fis1a, fis1b, fis2])
    db.commit()
    
    cod1a = CodigoDisciplina(codigo="FIS001A", curso_codigo="CC", conceito_id="CC-FIS1A")
    cod1b = CodigoDisciplina(codigo="FIS001B", curso_codigo="CC", conceito_id="CC-FIS1B")
    cod2 = CodigoDisciplina(codigo="FIS002", curso_codigo="CC", conceito_id="CC-FIS2")
    db.add_all([cod1a, cod1b, cod2])
    
    # Pré-requisitos de Física II (Física I-A ou Física I-B no grupo_alternativo 1)
    prereq1 = PreRequisito(curso_codigo="CC", conceito_id="CC-FIS2", conceito_prerequisito_id="CC-FIS1A", grupo_alternativo=1)
    prereq2 = PreRequisito(curso_codigo="CC", conceito_id="CC-FIS2", conceito_prerequisito_id="CC-FIS1B", grupo_alternativo=1)
    db.add_all([prereq1, prereq2])
    
    vinc = VinculoCurricular(curso_codigo="CC", conceito_id="CC-FIS2", periodicidade_oferta="par")
    db.add(vinc)
    
    # Aluno 1: Aprovado em Física I-A (Apto)
    aluno1 = Aluno(matricula="1001", curso_codigo="CC")
    hist1 = Historico(aluno_matricula="1001", curso_codigo="CC", disciplina_codigo="FIS001A", periodo_letivo="2025/1", situacao="aprovado")
    
    # Aluno 2: Aprovado em Física I-B (Apto)
    aluno2 = Aluno(matricula="1002", curso_codigo="CC")
    hist2 = Historico(aluno_matricula="1002", curso_codigo="CC", disciplina_codigo="FIS001B", periodo_letivo="2025/1", situacao="aprovado")
    
    # Aluno 3: Reprovado em Física I-A, não fez I-B (Não Apto)
    aluno3 = Aluno(matricula="1003", curso_codigo="CC")
    hist3 = Historico(aluno_matricula="1003", curso_codigo="CC", disciplina_codigo="FIS001A", periodo_letivo="2025/1", situacao="reprovado")
    
    db.add_all([aluno1, aluno2, aluno3])
    db.add_all([hist1, hist2, hist3])
    db.commit()
    
    # Execução
    resultado = grupo_b(db, "CC", "CC-FIS2")
    
    # Asserções
    assert "1001" in resultado
    assert "1002" in resultado
    assert "1003" not in resultado
    assert len(resultado) == 2


def test_exclusao_alunos_evadidos_rn05(db):
    # Setup: Cálculo II exige Cálculo I
    calc1 = ConceitoDisciplina(id="CC-CALC1", curso_codigo="CC", nome_normalizado="CALCULO I")
    calc2 = ConceitoDisciplina(id="CC-CALC2", curso_codigo="CC", nome_normalizado="CALCULO II")
    db.add_all([calc1, calc2])
    db.commit()
    
    cod1 = CodigoDisciplina(codigo="AL0001", curso_codigo="CC", conceito_id="CC-CALC1")
    cod2 = CodigoDisciplina(codigo="AL0002", curso_codigo="CC", conceito_id="CC-CALC2")
    db.add_all([cod1, cod2])
    
    prereq = PreRequisito(curso_codigo="CC", conceito_id="CC-CALC2", conceito_prerequisito_id="CC-CALC1")
    db.add(prereq)
    
    vinc = VinculoCurricular(curso_codigo="CC", conceito_id="CC-CALC2", periodicidade_oferta="par")
    db.add(vinc)
    
    # Aluno 1: Passou em Cálculo I e continua regular (Grupo B)
    aluno1 = Aluno(matricula="1001", curso_codigo="CC")
    hist1 = Historico(aluno_matricula="1001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/1", situacao="aprovado", situacao_matricula="Aluno Regular")
    
    # Aluno 2: Passou em Cálculo I mas depois evadiu por Abandono (Ignorado)
    aluno2 = Aluno(matricula="1002", curso_codigo="CC")
    hist2_1 = Historico(aluno_matricula="1002", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/1", situacao="aprovado", situacao_matricula="Aluno Regular")
    hist2_2 = Historico(aluno_matricula="1002", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2025/2", situacao="reprovado", situacao_matricula="Abandono")
    
    db.add_all([aluno1, aluno2])
    db.add_all([hist1, hist2_1, hist2_2])
    db.commit()
    
    # Execução
    resultado = grupo_b(db, "CC", "CC-CALC2")
    
    # Asserções
    assert "1001" in resultado
    assert "1002" not in resultado  # Deve ser filtrado pela evasão no histórico mais recente
    assert len(resultado) == 1


def test_grupo_c(db):
    # Setup: Cálculo II exige Cálculo I
    calc1 = ConceitoDisciplina(id="CC-CALC1", curso_codigo="CC", nome_normalizado="CALCULO I")
    calc2 = ConceitoDisciplina(id="CC-CALC2", curso_codigo="CC", nome_normalizado="CALCULO II")
    db.add_all([calc1, calc2])
    db.commit()
    
    cod1 = CodigoDisciplina(codigo="AL0001", curso_codigo="CC", conceito_id="CC-CALC1")
    cod2 = CodigoDisciplina(codigo="AL0002", curso_codigo="CC", conceito_id="CC-CALC2")
    db.add_all([cod1, cod2])
    
    prereq = PreRequisito(curso_codigo="CC", conceito_id="CC-CALC2", conceito_prerequisito_id="CC-CALC1")
    db.add(prereq)
    
    # Adicionamos históricos antigos para calcular a taxa de aprovação de Cálculo I (Nível 1)
    # 3 aprovados e 1 reprovado no total -> taxa = 3/4 = 0.75
    hist_antigo_1 = Historico(aluno_matricula="9001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2024/1", situacao="aprovado")
    hist_antigo_2 = Historico(aluno_matricula="9002", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2024/1", situacao="aprovado")
    hist_antigo_3 = Historico(aluno_matricula="9003", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2024/1", situacao="aprovado")
    hist_antigo_4 = Historico(aluno_matricula="9004", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2024/1", situacao="reprovado")
    db.add_all([hist_antigo_1, hist_antigo_2, hist_antigo_3, hist_antigo_4])
    db.commit()
    
    # Aluno 1: Cursando Cálculo I no período letivo atual 2026/1 (Grupo C)
    aluno1 = Aluno(matricula="1001", curso_codigo="CC")
    hist1 = Historico(aluno_matricula="1001", curso_codigo="CC", disciplina_codigo="AL0001", periodo_letivo="2026/1", situacao="cursando")
    
    # Aluno 2: Não está fazendo Cálculo I (Não entra no Grupo C)
    aluno2 = Aluno(matricula="1002", curso_codigo="CC")
    
    db.add_all([aluno1, aluno2])
    db.add_all([hist1])
    db.commit()
    
    # Execução
    resultado = grupo_c(db, "CC", "CC-CALC2", "2026/1")
    
    # Asserções
    assert len(resultado) == 1
    assert resultado[0].matricula == "1001"
    assert resultado[0].probabilidade_aprovacao == 0.75


def test_demanda_estimada(db):
    # Setup: Física II exige Física I
    fis1 = ConceitoDisciplina(id="CC-FIS1", curso_codigo="CC", nome_normalizado="FISICA I")
    fis2 = ConceitoDisciplina(id="CC-FIS2", curso_codigo="CC", nome_normalizado="FISICA II")
    db.add_all([fis1, fis2])
    db.commit()
    
    cod1 = CodigoDisciplina(codigo="FIS001", curso_codigo="CC", conceito_id="CC-FIS1")
    cod2 = CodigoDisciplina(codigo="FIS002", curso_codigo="CC", conceito_id="CC-FIS2")
    db.add_all([cod1, cod2])
    
    prereq = PreRequisito(curso_codigo="CC", conceito_id="CC-FIS2", conceito_prerequisito_id="CC-FIS1")
    db.add(prereq)
    
    # Histórico de Física I para calcular taxa (1 aprovado, 1 reprovado -> taxa = 0.5)
    h_ant_1 = Historico(aluno_matricula="9001", curso_codigo="CC", disciplina_codigo="FIS001", periodo_letivo="2024/1", situacao="aprovado")
    h_ant_2 = Historico(aluno_matricula="9002", curso_codigo="CC", disciplina_codigo="FIS001", periodo_letivo="2024/1", situacao="reprovado")
    db.add_all([h_ant_1, h_ant_2])
    db.commit()
    
    # Aluno 1: Cursando Física II agora em 2026/1 (Grupo A)
    aluno1 = Aluno(matricula="1001", curso_codigo="CC")
    h1 = Historico(aluno_matricula="1001", curso_codigo="CC", disciplina_codigo="FIS002", periodo_letivo="2026/1", situacao="cursando")
    
    # Aluno 2: Passou em Física I (Grupo B)
    aluno2 = Aluno(matricula="1002", curso_codigo="CC")
    h2 = Historico(aluno_matricula="1002", curso_codigo="CC", disciplina_codigo="FIS001", periodo_letivo="2025/1", situacao="aprovado")
    
    # Aluno 3: Cursando Física I agora em 2026/1 (Grupo C com prob = 0.5)
    aluno3 = Aluno(matricula="1003", curso_codigo="CC")
    h3 = Historico(aluno_matricula="1003", curso_codigo="CC", disciplina_codigo="FIS001", periodo_letivo="2026/1", situacao="cursando")
    
    db.add_all([aluno1, aluno2, aluno3])
    db.add_all([h1, h2, h3])
    db.commit()
    
    # Execução
    demanda = demanda_estimada(db, "CC", "CC-FIS2", "2026/1")
    
    # Grupo A = 1 (aluno1)
    # Grupo B = 1 (aluno2)
    # Grupo C = 0.6667 (aluno3, prob 2/3)
    # Total = 1 + 1 + 0.6667 = 2.6667
    assert round(demanda, 4) == 2.6667
