"""
Ponto único de conexão com o banco de dados.

O SQLAlchemy funciona em três camadas, de baixo para cima:

1. `engine`  — sabe COMO conectar no Postgres (endereço, usuário, senha).
2. `SessionLocal` — uma "conversa" com o banco: você abre, faz operações
   (SELECT/INSERT/UPDATE), confirma (commit) ou desfaz (rollback), fecha.
3. `Base` — classe da qual todos os modelos (tabelas) em models.py herdam.
   É o que permite ao SQLAlchemy saber "isto aqui é uma tabela".

`get_db()` é uma dependency do FastAPI: cada rota da API que precisar
conversar com o banco declara `db: Session = Depends(get_db)` no argumento,
e o FastAPI cuida de abrir a sessão antes da requisição e fechar depois —
mesmo se a rota der erro no meio do caminho.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
