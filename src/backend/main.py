"""
Ponto de entrada do backend.

Rodar com (dentro de src/backend, com o venv ativado):
    uvicorn main:app --reload

Depois abra http://localhost:8000/docs — o FastAPI gera essa tela
automaticamente (é um dos motivos dele ter sido escolhido no ADR 0004):
uma página onde dá pra testar cada endpoint da API sem escrever código.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sistema de Apoio à Decisão de Oferta de Disciplinas",
    description="API para estimar demanda de disciplinas — UNIPAMPA",
    version="0.1.0",
)

# Libera o frontend (React, rodando em outra porta durante o desenvolvimento)
# a chamar esta API. Em produção, restrinja allow_origins ao domínio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # porta padrão do Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Endpoint simples para confirmar que o servidor está de pé."""
    return {"status": "ok"}


from api.auth import router as auth_router
from api.demanda import router as demanda_router

app.include_router(auth_router, prefix="/auth", tags=["autenticação"])
app.include_router(demanda_router, prefix="/demanda", tags=["demanda"])
