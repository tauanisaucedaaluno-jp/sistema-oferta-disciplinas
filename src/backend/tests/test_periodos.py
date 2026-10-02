import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    PeriodoLetivo,
)
from api.auth import obter_usuario_atual


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

    usuario_mock = Usuario(
        id=1,
        email="coordenador@unipampa.edu.br",
        senha_hash="dummy",
        papel="coordenador",
        ativo=True,
    )
    session.add(usuario_mock)

    # Cria curso e dados de histórico de teste para 2026/1 e 2025/2
    curso = Curso(codigo="CC", nome="Ciência da Computação")
    aluno = Aluno(matricula="1001", curso_codigo="CC")
    session.add_all([curso, aluno])
    session.commit()

    hist1 = Historico(
        aluno_matricula="1001",
        curso_codigo="CC",
        disciplina_codigo="AL0001",
        periodo_letivo="2026/1",
        situacao="cursando",
    )
    hist2 = Historico(
        aluno_matricula="1001",
        curso_codigo="CC",
        disciplina_codigo="AL0001",
        periodo_letivo="2025/2",
        situacao="aprovado",
    )
    p1 = PeriodoLetivo(codigo="2026/1", ano=2026, semestre=1, descricao="2026/1", is_atual=True)
    p2 = PeriodoLetivo(codigo="2025/2", ano=2025, semestre=2, descricao="2025/2", is_atual=False)
    session.add_all([hist1, hist2, p1, p2])
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


def test_listar_periodos(client_and_db):
    client, session = client_and_db

    response = client.get("/demanda/periodos")
    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 2
    codigos = [p["codigo"] for p in data]
    assert "2026/1" in codigos
    assert "2025/2" in codigos

    # 2026/1 deve ser o primeiro por ser mais recente
    assert codigos[0] == "2026/1"
    item_2026_1 = next(p for p in data if p["codigo"] == "2026/1")
    assert item_2026_1["total_cursando"] == 1
    assert item_2026_1["is_atual"] is True


def test_criar_periodo_sucesso(client_and_db):
    client, session = client_and_db

    payload = {
        "periodo": "2027/1",
        "descricao": "Planejamento 2027/1",
        "is_atual": False,
    }
    response = client.post("/demanda/periodos", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sucesso"
    assert data["codigo"] == "2027/1"

    # Confirma que aparece na listagem
    res_list = client.get("/demanda/periodos")
    codigos = [p["codigo"] for p in res_list.json()]
    assert "2027/1" in codigos


def test_criar_periodo_invalido(client_and_db):
    client, session = client_and_db

    # Semestre 3 não existe (apenas 1 ou 2)
    response = client.post("/demanda/periodos", json={"periodo": "2027/3"})
    assert response.status_code == 400

    # Formato inválido
    response2 = client.post("/demanda/periodos", json={"periodo": "semestre-invalido"})
    assert response2.status_code == 400


def test_excluir_periodo(client_and_db):
    client, session = client_and_db

    # Verifica que 2025/2 tem histórico
    assert session.query(Historico).filter(Historico.periodo_letivo == "2025/2").count() == 1

    # Exclui 2025/2
    response = client.delete("/demanda/periodos/2025/2")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sucesso"
    assert data["linhas_removidas"] == 1

    # Confirma que 2025/2 não tem mais histórico e 2026/1 permanece intacto
    assert session.query(Historico).filter(Historico.periodo_letivo == "2025/2").count() == 0
    assert session.query(Historico).filter(Historico.periodo_letivo == "2026/1").count() == 1


def test_periodo_sem_dados_demanda_zerada(client_and_db):
    """Garante que curso sem alunos ou histórico acadêmico retorna demandas com contagens zeradas."""
    client, session = client_and_db

    # Cria conceito e vínculo curricular para um curso sem alunos matriculados
    calc1 = ConceitoDisciplina(id="NOVO-CALC1", curso_codigo="CURSO_NOVO", nome_normalizado="CALCULO NOVO")
    session.add(calc1)
    session.commit()

    cod_calc1 = CodigoDisciplina(codigo="NV0001", curso_codigo="CURSO_NOVO", conceito_id="NOVO-CALC1")
    vinc = VinculoCurricular(curso_codigo="CURSO_NOVO", conceito_id="NOVO-CALC1", periodo_sugerido=1, periodicidade_oferta="ambos")
    session.add_all([cod_calc1, vinc])
    session.commit()

    # Cria o novo semestre 2028/1
    res_criar = client.post("/demanda/periodos", json={"periodo": "2028/1", "descricao": "Semestre Futuro"})
    assert res_criar.status_code == 200

    # Consulta demandas para o curso sem histórico
    res_demanda = client.get("/demanda?curso_codigo=CURSO_NOVO&periodo_atual=2028/1&modo=regular")
    assert res_demanda.status_code == 200
    demandas = res_demanda.json()
    assert len(demandas) >= 1
    item = demandas[0]
    # Disciplina deve estar listada, mas com grupos zerados
    assert item["grupo_a_qtd"] == 0
    assert item["grupo_b_qtd"] == 0
    assert item["grupo_c_qtd"] == 0
    assert item["demanda_estimada"] == 0.0
    assert item["total_alunos"] == 0


def test_isolamento_demandas_entre_periodos(client_and_db):
    """Garante que a demanda de um período anterior (2026/1) não é afetada pela criação de 2027/1."""
    client, session = client_and_db
    from db.models import DemandaSnapshot

    # Salva snapshot para 2026/1
    snap_26 = DemandaSnapshot(
        periodo_codigo="2026/1",
        curso_codigo="CC",
        conceito_id="CC-CALC1",
        grupo_a_qtd=5,
        grupo_b_qtd=10,
        grupo_c_qtd=2,
        grupo_a_prob=2.5,
        grupo_c_prob=1.4,
        demanda_estimada=13.9,
    )
    session.add(snap_26)
    session.commit()

    # Cria o período 2027/1 e seu próprio snapshot com dados diferentes
    client.post("/demanda/periodos", json={"periodo": "2027/1", "descricao": "Semestre 2027/1"})
    snap_27 = DemandaSnapshot(
        periodo_codigo="2027/1",
        curso_codigo="CC",
        conceito_id="CC-CALC1",
        grupo_a_qtd=25,
        grupo_b_qtd=50,
        grupo_c_qtd=12,
        grupo_a_prob=12.5,
        grupo_c_prob=8.4,
        demanda_estimada=70.9,
    )
    session.add(snap_27)
    session.commit()

    # Consulta 2026/1: deve retornar exatamente os dados originais de 2026/1
    res_26 = client.get("/demanda?curso_codigo=CC&periodo_atual=2026/1")
    assert res_26.status_code == 200
    dados_26 = res_26.json()
    item_26 = next(d for d in dados_26 if d["conceito_id"] == "CC-CALC1")
    assert item_26["grupo_a_qtd"] == 5
    assert item_26["grupo_b_qtd"] == 10
    assert item_26["grupo_c_qtd"] == 2
    assert item_26["demanda_estimada"] == 13.9

    # Consulta 2027/1: deve retornar os dados de 2027/1
    res_27 = client.get("/demanda?curso_codigo=CC&periodo_atual=2027/1")
    assert res_27.status_code == 200
    dados_27 = res_27.json()
    item_27 = next(d for d in dados_27 if d["conceito_id"] == "CC-CALC1")
    assert item_27["grupo_a_qtd"] == 25
    assert item_27["grupo_b_qtd"] == 50
    assert item_27["grupo_c_qtd"] == 12
    assert item_27["demanda_estimada"] == 70.9


