import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from main import app
from db.database import Base, get_db
from db.models import Usuario, PeriodoLetivo, DemandaSnapshot
from config import settings
from api.auth import obter_usuario_atual


@pytest.fixture(name="client_db")
def fixture_client_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    # Cria usuário 1 (coordenador original)
    user1 = Usuario(
        id=1,
        email="coordenador1@unipampa.edu.br",
        senha_hash="hash1",
        papel="coordenador",
        ativo=True,
    )
    session.add(user1)
    session.commit()

    # Cria período para usuário 1
    p1 = PeriodoLetivo(
        usuario_id=1,
        codigo="2026/1",
        ano=2026,
        semestre=1,
        descricao="2026/1",
        is_atual=True,
    )
    session.add(p1)
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        yield client, session, user1
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(engine)


def test_solicitar_acesso_e_definir_senha(client_db):
    client, session, _ = client_db

    # 1. Solicita acesso para nova coordenadora
    res_solicitar = client.post("/auth/solicitar-acesso", json={"email": "coordenadora.maria@unipampa.edu.br"})
    assert res_solicitar.status_code == 200
    data_sol = res_solicitar.json()
    assert data_sol["status"] == "sucesso"
    assert "token=" in data_sol["link_ativacao"]

    token = data_sol["link_ativacao"].split("token=")[1]

    # Verifica que usuário foi cadastrado como inativo temporariamente
    novo_user = session.query(Usuario).filter(Usuario.email == "coordenadora.maria@unipampa.edu.br").first()
    assert novo_user is not None
    assert novo_user.ativo is False
    assert novo_user.senha_hash is None

    # 2. Tenta definir senha curta (menos de 6 caracteres) -> Deve falhar
    res_curta = client.post("/auth/definir-senha", json={"token": token, "nova_senha": "123"})
    assert res_curta.status_code == 400

    # 3. Define senha válida
    res_def = client.post("/auth/definir-senha", json={"token": token, "nova_senha": "senhaSegura123!"})
    assert res_def.status_code == 200
    data_def = res_def.json()
    assert data_def["status"] == "sucesso"
    assert "access_token" in data_def

    # Verifica que agora está ativo e tem senha hash válida
    session.refresh(novo_user)
    assert novo_user.ativo is True
    assert novo_user.senha_hash is not None

    # 4. Consegue fazer login normalmente com a nova senha
    res_login = client.post("/auth/login", json={"email": "coordenadora.maria@unipampa.edu.br", "senha": "senhaSegura123!"})
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()


def test_isolamento_de_semestres_entre_coordenadores(client_db):
    """
    Garante que cada coordenador tem sua própria visão isolada:
    - O novo coordenador começa com 0 semestres cadastrados.
    - O coordenador 1 não vê os semestres do coordenador 2 e vice-versa.
    """
    client, session, user1 = client_db

    # Cria e ativa novo usuário 2
    user2 = Usuario(
        id=2,
        email="coordenador2@unipampa.edu.br",
        senha_hash="hash2",
        papel="coordenador",
        ativo=True,
    )
    session.add(user2)
    session.commit()

    # Simula autenticação como user2
    app.dependency_overrides[obter_usuario_atual] = lambda: user2

    # 1. Usuário 2 consulta períodos: DEVE RETORNAR VAZIO (nenhum semestre cadastrado ainda)
    res_u2_periodos = client.get("/demanda/periodos")
    assert res_u2_periodos.status_code == 200
    assert res_u2_periodos.json() == []

    # 2. Usuário 2 cadastra seu próprio semestre 2027/1
    res_criar = client.post("/demanda/periodos", json={"periodo": "2027/1", "descricao": "Semestre U2"})
    assert res_criar.status_code == 200

    # Agora usuário 2 vê apenas 2027/1
    res_u2_novo = client.get("/demanda/periodos")
    codigos_u2 = [p["codigo"] for p in res_u2_novo.json()]
    assert codigos_u2 == ["2027/1"]
    assert "2026/1" not in codigos_u2

    # 3. Alterna para autenticação como user1
    app.dependency_overrides[obter_usuario_atual] = lambda: user1

    # Usuário 1 DEVE continuar vendo apenas 2026/1 e NÃO ver 2027/1 de user2
    res_u1 = client.get("/demanda/periodos")
    codigos_u1 = [p["codigo"] for p in res_u1.json()]
    assert "2026/1" in codigos_u1
    assert "2027/1" not in codigos_u1


def test_cadastro_direto_na_plataforma(client_db):
    """Garante que o coordenador pode criar sua conta e senha diretamente na plataforma sem e-mail."""
    client, session, _ = client_db

    # 1. Tenta cadastrar com senha curta (< 6 caracteres)
    res_curta = client.post("/auth/cadastrar", json={"email": "novo.coord@unipampa.edu.br", "senha": "123"})
    assert res_curta.status_code == 400

    # 2. Cadastro direto com sucesso
    res_cad = client.post("/auth/cadastrar", json={"email": "novo.coord@unipampa.edu.br", "senha": "senhaSegura123!"})
    assert res_cad.status_code == 200
    data_cad = res_cad.json()
    assert data_cad["status"] == "sucesso"
    assert "access_token" in data_cad
    assert data_cad["email"] == "novo.coord@unipampa.edu.br"

    # Confirma que o usuário foi gravado ativo no banco
    u_db = session.query(Usuario).filter(Usuario.email == "novo.coord@unipampa.edu.br").first()
    assert u_db is not None
    assert u_db.ativo is True
    assert u_db.senha_hash is not None

    # Tenta cadastrar novamente com o mesmo e-mail -> Deve avisar que já existe
    res_dup = client.post("/auth/cadastrar", json={"email": "novo.coord@unipampa.edu.br", "senha": "outraSenha123!"})
    assert res_dup.status_code == 400


def test_allowed_emails_restringe_cadastro_e_login(client_db, monkeypatch):
    """Com ALLOWED_EMAILS preenchida, só o e-mail da lista cadastra, solicita acesso e entra."""
    client, _, _ = client_db
    monkeypatch.setattr(settings, "allowed_emails", "natalia@unipampa.edu.br")

    res_cadastro = client.post(
        "/auth/cadastrar",
        json={"email": "outro@unipampa.edu.br", "senha": "senhaSegura123!"},
    )
    assert res_cadastro.status_code == 403

    res_solicitar = client.post("/auth/solicitar-acesso", json={"email": "outro@unipampa.edu.br"})
    assert res_solicitar.status_code == 403

    res_login_outro = client.post(
        "/auth/login",
        json={"email": "coordenador1@unipampa.edu.br", "senha": "qualquer"},
    )
    assert res_login_outro.status_code == 403

    res_ok = client.post(
        "/auth/cadastrar",
        json={"email": "Natalia@unipampa.edu.br", "senha": "senhaSegura123!"},
    )
    assert res_ok.status_code == 200

    res_login = client.post(
        "/auth/login",
        json={"email": "Natalia@unipampa.edu.br", "senha": "senhaSegura123!"},
    )
    assert res_login.status_code == 200


def test_novo_semestre_nasce_zerado_sem_puxar_2026_1(client_db):
    """
    Garante que ao criar um novo semestre, seus dados nascem 100% ZERADOS,
    não puxando matrículas nem dados de 2026/1.
    """
    client, session, user1 = client_db
    from db.models import Curso, ConceitoDisciplina, CodigoDisciplina, VinculoCurricular, Historico

    # Configura curso e disciplina curricular
    curso = Curso(codigo="ALEC", nome="Engenharia Civil")
    conc = ConceitoDisciplina(id="ALEC-CALC1", curso_codigo="ALEC", nome_normalizado="CALCULO I")
    cod = CodigoDisciplina(codigo="AL0001", curso_codigo="ALEC", conceito_id="ALEC-CALC1")
    vinc = VinculoCurricular(curso_codigo="ALEC", conceito_id="ALEC-CALC1", periodo_sugerido=1, periodicidade_oferta="ambos")
    session.add_all([curso, conc, cod, vinc])
    session.commit()

    # Adiciona registros de histórico com alunos cursando em 2026/1
    h26 = Historico(
        aluno_matricula="99001",
        curso_codigo="ALEC",
        disciplina_codigo="AL0001",
        periodo_letivo="2026/1",
        situacao="cursando",
    )
    session.add(h26)
    session.commit()

    app.dependency_overrides[obter_usuario_atual] = lambda: user1

    # Cria o novo semestre 2027/2
    res_criar = client.post("/demanda/periodos", json={"periodo": "2027/2", "descricao": "Semestre Futuro"})
    assert res_criar.status_code == 200

    # Consulta a demanda de 2027/2
    res_demanda = client.get("/demanda?curso_codigo=ALEC&periodo_atual=2027/2")
    assert res_demanda.status_code == 200
    dados = res_demanda.json()
    assert len(dados) >= 1

    item = next(d for d in dados if d["conceito_id"] == "ALEC-CALC1")
    # DEVE NASCER 100% ZERADO, sem puxar nada de 2026/1!
    assert item["grupo_a_qtd"] == 0
    assert item["grupo_b_qtd"] == 0
    assert item["grupo_c_qtd"] == 0
    assert item["demanda_estimada"] == 0.0
    assert item["total_alunos"] == 0

