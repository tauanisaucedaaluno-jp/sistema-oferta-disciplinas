# Como rodar o ambiente localmente

## 1. Banco de dados (PostgreSQL via Docker)

```bash
docker compose up -d
```

Isso sobe um Postgres em `localhost:5432` com usuário `oferta`, senha
`oferta_dev_local`, banco `oferta_disciplinas` (ver `docker-compose.yml`).
Não precisa instalar Postgres na máquina.

## 2. Backend (FastAPI)

```bash
cd src/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # ajuste se necessário
```

Depois de configurar o Alembic (ver Epic 0, Issue 3 no guia de
implementação) e rodar a primeira migração:

```bash
alembic upgrade head
```

Suba o servidor:

```bash
uvicorn main:app --reload
```

Abra `http://localhost:8000/docs` — Swagger UI gerado automaticamente
pelo FastAPI, dá pra testar os endpoints sem escrever código.

## 3. Frontend (React)

Ainda não criado (Epic 0, Issue 4). Quando criar:

```bash
cd src/frontend
npm create vite@latest . -- --template react
npm install
npm run dev
```

Sobe em `http://localhost:5173` por padrão — já liberado no CORS do
backend (`main.py`).
