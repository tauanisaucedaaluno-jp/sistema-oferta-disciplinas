import os
import sys
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from main import app
from db.database import Base, get_db
from db.models import (
    Usuario,
    Curso,
    Aluno,
    Historico,
    ConceitoDisciplina,
    CodigoDisciplina,
    VinculoCurricular,
    PreRequisito,
    LogAcesso,
)
from api.auth import obter_usuario_atual



# CSV mínimo de currículo para teste
CSV_CURRICULO_TESTE = """cod_curso;curso;num_versao;versao;situacao;cod_disciplina;nome_disciplina;tipo_disciplina;periodo_ideal;pre_requisitos;equivalencias
CC;Ciência da Computação;2023;CORRENTE;ATIVA;AL0001;Cálculo I;Obrigatória;1;;
CC;Ciência da Computação;2023;CORRENTE;ATIVA;AL0002;Cálculo II;Obrigatória;2;AL0001;
"""

# CSV mínimo de histórico escolar para teste
CSV_HISTORICO_TESTE = """matrícula;cod_curso;curso;versão PPC;ano;período;média final;conceito;situação na disciplina;cod_ativ_curric;nome_ativ_curric;créditos;ch total;estrutura curric.;ch mínima estrutura;forma de ingresso;situação da matrícula;ano evasão;nome_curso_diploma;cod_turma;docentes
2023001;CC;Ciência da Computação;2023;2026;1. Semestre;;;Matrícula;AL0001;Cálculo I;4;60;Obrigatória;60;Vestibular;Aluno Regular;;;;
2023002;CC;Ciência da Computação;2023;2025;2. Semestre;8.0;;Aprovado com nota;AL0001;Cálculo I;4;60;Obrigatória;60;Vestibular;Aluno Regular;;;;
2023002;CC;Ciência da Computação;2023;2026;1. Semestre;;;Matrícula;AL0002;Cálculo II;4;60;Obrigatória;60;Vestibular;Aluno Regular;;;;
"""


from sqlalchemy.pool import StaticPool


@pytest.fixture(name="client_and_db")
def fixture_client_and_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()


    # Cria usuário coordenador autenticado para os testes
    usuario_mock = Usuario(
        id=1,
        email="coordenador@unipampa.edu.br",
        senha_hash="dummy",
        papel="coordenador",
        ativo=True,
    )
    session.add(usuario_mock)
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    def override_obter_usuario_atual():
        return usuario_mock

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[obter_usuario_atual] = override_obter_usuario_atual

    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(engine)


def test_upload_historico_e_curriculo(client_and_db):
    client, session = client_and_db

    files = [
        ("historicos", ("historico_cc.csv", io.BytesIO(CSV_HISTORICO_TESTE.encode("utf-8")), "text/csv")),
    ]
    curriculo_file = ("curriculo", ("curriculo.csv", io.BytesIO(CSV_CURRICULO_TESTE.encode("utf-8")), "text/csv"))

    response = client.post("/importacao/upload?ignorar_minimo=true", files=files + [curriculo_file])
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "sucesso"
    assert data["total_arquivos"] == 1
    assert data["total_linhas_historico"] == 3
    assert data["total_alunos"] == 2
    assert "tempo_segundos" in data

    # Valida se os dados foram salvos no banco
    assert session.query(Aluno).count() == 2
    assert session.query(Historico).count() == 3
    assert session.query(ConceitoDisciplina).count() > 0


def test_upload_menos_de_seis_arquivos_rejeitado(client_and_db):
    """Garante que tentar enviar menos de 6 arquivos de histórico é rejeitado com status 400."""
    client, session = client_and_db

    files = [
        ("historicos", ("historico_cc.csv", io.BytesIO(CSV_HISTORICO_TESTE.encode("utf-8")), "text/csv")),
    ]
    response = client.post("/importacao/upload", files=files)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "no mínimo 6 arquivos" in detail


def test_upload_sem_arquivos(client_and_db):
    client, session = client_and_db
    response = client.post("/importacao/upload", files=[])
    # FastAPI valida que campo historicos é obrigatório
    assert response.status_code == 422


def test_upload_arquivo_invalido(client_and_db):
    client, session = client_and_db
    files = [
        ("historicos", ("arquivo_executavel.exe", io.BytesIO(b"dummy binary"), "application/octet-stream")),
    ]
    response = client.post("/importacao/upload?ignorar_minimo=true", files=files)
    assert response.status_code == 400
    assert "Apenas arquivos .csv ou .xlsx" in response.json()["detail"]


def test_upload_com_filtro_ano_corte(client_and_db, monkeypatch):
    """Garante que registros de anos anteriores ao ano de corte são descartados no upload."""
    client, session = client_and_db
    from config import settings
    monkeypatch.setattr(settings, "historico_ano_corte", 2020)

    # CSV contendo linha de 2008 (anterior ao corte 2020) e linhas de 2025/2026
    csv_com_anos_antigos = """matrícula;cod_curso;curso;versão PPC;ano;período;média final;conceito;situação na disciplina;cod_ativ_curric;nome_ativ_curric;créditos;ch total;estrutura curric.;ch mínima estrutura;forma de ingresso;situação da matrícula;ano evasão;nome_curso_diploma;cod_turma;docentes
2008001;CC;Ciência da Computação;2008;2008;1. Semestre;5.0;;Aprovado com nota;AL0001;Cálculo I;4;60;Obrigatória;60;Vestibular;Formado;2012;;;
2023001;CC;Ciência da Computação;2023;2026;1. Semestre;;;Matrícula;AL0001;Cálculo I;4;60;Obrigatória;60;Vestibular;Aluno Regular;;;;
2023002;CC;Ciência da Computação;2023;2025;2. Semestre;8.0;;Aprovado com nota;AL0001;Cálculo I;4;60;Obrigatória;60;Vestibular;Aluno Regular;;;;
"""
    files = [
        ("historicos", ("historico_cc.csv", io.BytesIO(csv_com_anos_antigos.encode("utf-8")), "text/csv")),
    ]
    curriculo_file = ("curriculo", ("curriculo.csv", io.BytesIO(CSV_CURRICULO_TESTE.encode("utf-8")), "text/csv"))

    response = client.post("/importacao/upload?ignorar_minimo=true", files=files + [curriculo_file])
    assert response.status_code == 200
    data = response.json()

    # O registro de 2008 foi descartado pelo corte, mantendo apenas 2 registros (2025 e 2026)
    assert data["total_linhas_historico"] == 2
    assert session.query(Historico).count() == 2
    # Aluno de 2008 não deve ter sido inserido
    assert session.query(Aluno).filter(Aluno.matricula == "2008001").first() is None

