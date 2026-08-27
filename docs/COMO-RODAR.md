# Como rodar o sistema — OfertaPampa (dados de teste)

Guia atualizado em: 2026-08-27

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e **rodando**
- [Python 3.11+](https://www.python.org/) com `venv`
- [Node.js 18+](https://nodejs.org/) com `npm`
- Você está na raiz do repositório: `sistema-oferta-disciplinas/`

---

## Passo 1 — Subir o banco de dados (Postgres)

```powershell
docker compose up -d
```

Isso sobe o Postgres na porta `5432` em background. Para verificar:

```powershell
docker compose ps
```

A coluna `Status` deve mostrar `running`.

---

## Passo 2 — Configurar o backend

Já existe um arquivo `.env` pronto em `src/backend/`. Se não existir, copie:

```powershell
Copy-Item src\backend\.env.example src\backend\.env
```

Ative o ambiente virtual (se ainda não estiver ativado):

```powershell
.\venv\Scripts\Activate.ps1
```

> Se aparecer erro de política de execução, rode antes:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Instale as dependências (só na primeira vez):

```powershell
pip install -r src\backend\requirements.txt
```

---

## Passo 3 — Criar as tabelas e carregar os dados de teste

### 3a. Aplicar as migrações (criar tabelas)

```powershell
cd src\backend
alembic upgrade head
cd ..\..
```

Deve aparecer: `Running upgrade -> 84055d28018b ...` e depois `Running upgrade ... -> 26421a10895a ...`

### 3b. Inserir os dados falsos

Conecte ao banco e rode o seed. Opção 1 — via `psql` (se instalado):

```powershell
psql -h localhost -U oferta -d oferta_disciplinas -f data\sample\seed.sql
```

Senha quando pedir: `oferta_dev_local`

Opção 2 — via Docker (sem precisar do `psql` local):

```powershell
docker exec -i oferta-disciplinas-db psql -U oferta -d oferta_disciplinas < data\sample\seed.sql
```

Se rodar corretamente, você verá saídas como `DELETE 0`, `INSERT 0 2`, `INSERT 0 3`, etc.

---

## Passo 4 — Iniciar o backend

```powershell
cd src\backend
uvicorn main:app --reload --port 8000
```

Teste no navegador: http://localhost:8000/health

Deve retornar: `{"status":"ok"}`

Documentação interativa da API (Swagger): http://localhost:8000/docs

---

## Passo 5 — Iniciar o frontend

Em **outro terminal** (sem fechar o backend):

```powershell
cd src\frontend
npm run dev
```

Abra no navegador: http://localhost:5173

---

## Passo 6 — Fazer login e testar

Na tela de login, use:

| Campo | Valor |
|-------|-------|
| E-mail | `coordenador@unipampa.edu.br` |
| Senha | `admin123` |

### O que testar no sistema

1. **Login** → deve redirecionar para o Dashboard
2. **Filtro de curso** → selecionar `CC` (Ciência da Computação)
3. **Filtro de período** → selecionar `2026/1`
   - Deve aparecer 2 disciplinas: `C-CALC1` e `C-PROG1`
   - `C-CALC1` terá **1 aluno no Grupo A** (matrícula `2021002`, cursando em 2026/1)
4. **Clicar em uma disciplina** → abre a tela de Detalhe com Grupos A/B/C
5. **Botão Exportar CSV** → faz download de um arquivo `.csv`

---

## Parar tudo

```powershell
# Para o banco (preserva os dados):
docker compose stop

# Para apagar os dados e começar do zero:
docker compose down -v
```

---

## Resolução de problemas comuns

| Problema | Solução |
|----------|---------|
| `Connection refused` no backend | Verifique se o Docker está rodando e rode `docker compose up -d` |
| `alembic: command not found` | Certifique-se que o venv está ativado com `.\venv\Scripts\Activate.ps1` |
| Erro `detail: E-mail ou senha incorretos` | Rode o `seed.sql` novamente para recriar o usuário |
| Frontend mostra tela em branco | Abra o console do navegador (F12) e veja o erro; verifique se o backend está rodando |
| Porta `8000` em uso | Rode o backend em outra porta: `uvicorn main:app --reload --port 8001` — e ajuste `API_BASE` nos `.tsx` |
