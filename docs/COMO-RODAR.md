# Como rodar o sistema — OfertaPampa

Guia atualizado em: 2026-09-04

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

Isso sobe o Postgres na porta `5432` em background. Para verificar se está rodando:

```powershell
docker compose ps
```

A coluna `Status` deve mostrar `running` (ou `Up ...`).
> **Nota:** O banco utiliza um volume permanente (`oferta_disciplinas_dbdata`). Todos os dados reais importados ficam preservados automaticamente entre reinicializações.

---

## Passo 2 — Configurar o backend

Já existe um arquivo `.env` pronto em `src/backend/` e na raiz, apontando para o PostgreSQL:
`DATABASE_URL=postgresql+psycopg2://oferta:oferta_dev_local@localhost:5432/oferta_disciplinas`

Ative o ambiente virtual (se ainda não estiver ativado):

```powershell
.\venv\Scripts\Activate.ps1
```

> Se aparecer erro de política de execução no PowerShell, execute antes:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Instale as dependências (necessário apenas na primeira configuração):

```powershell
pip install -r src\backend\requirements.txt
```

---

## Passo 3 — Estrutura das Tabelas e Carga de Dados

### 3a. Aplicar as migrações (criar ou atualizar tabelas)

Caso o banco seja iniciado do zero, aplique as migrações:

```powershell
cd src\backend
alembic upgrade head
cd ..\..
```

### 3b. Carga de Dados (ETL)

O banco de dados do projeto já está populado com os **dados reais** dos 6 cursos de Engenharia (Agrícola, Civil, Elétrica, Mecânica, Software e Telecomunicações).

> ⚠️ **IMPORTANTE: NÃO execute o `seed.sql` nem o `seed_db.py` no dia a dia!**  
> Esses arquivos continham dados fictícios para testes iniciais. Executá-los inseriria dados falsos que se misturariam aos dados reais.

#### Como atualizar ou recarregar os dados reais:
Sempre que você receber novas matrizes curriculares ou históricos atualizados:
1. Coloque a matriz em `data/raw/` e os históricos na pasta `data/raw/historicos/`.
2. Execute o script de ETL:
   ```powershell
   python scripts/run_etl.py
   ```
   *O script limpa os dados acadêmicos anteriores, recarrega a base real do zero e garante que o usuário coordenador continue ativo.*

*(Opcional) Caso queira propositalmente rodar apenas os dados falsos para testes isolados:*
```powershell
python scripts/run_etl.py --sample
```

---

## Passo 4 — Iniciar o backend (FastAPI)

```powershell
cd src\backend
uvicorn main:app --reload --port 8000
```

Teste no navegador: http://localhost:8000/health  
Deve retornar: `{"status":"ok"}`

Documentação interativa da API (Swagger): http://localhost:8000/docs

---

## Passo 5 — Iniciar o frontend (React)

Em **outro terminal** (mantendo o backend aberto):

```powershell
cd src\frontend
npm run dev
```

Abra no navegador: http://localhost:5173

---

## Passo 6 — Fazer login e usar o sistema

Na tela de login, utilize o usuário padrão de coordenação:

| Campo | Valor |
|-------|-------|
| E-mail | `coordenador@unipampa.edu.br` |
| Senha | `admin123` |

### O que testar no sistema com dados reais

1. **Login** → redireciona diretamente para o Dashboard.
2. **Filtro de curso** → selecione qualquer um dos cursos reais carregados:
   - `ALES` — Engenharia de Software
   - `ALEC` — Engenharia Civil
   - `ALEE` — Engenharia Elétrica
   - `ALEM` — Engenharia Mecânica
   - `ALEA` — Engenharia Agrícola
   - `ALET` — Engenharia de Telecomunicações
3. **Filtro de período** → selecione o período letivo desejado (ex.: `2024/1`, `2024/2`, `2025/1`, etc.).
4. **Detalhe de Demanda** → clique em qualquer disciplina para ver a estimativa de alunos nos **Grupos A, B e C**.
5. **Exportar CSV** → baixa a listagem formatada para a tomada de decisão da coordenação.

---

## Parar o sistema

```powershell
# Para o container do banco sem perder nenhum dado:
docker compose stop

# Para religar quando for trabalhar novamente:
docker compose up -d
```

> 🛑 **Cuidado com a flag `-v`:**  
> O comando `docker compose down -v` apaga os volumes do Docker (apagando os dados reais do banco). Se precisar apenas parar, use sempre `docker compose stop` ou `docker compose down` (sem `-v`).

---

## Resolução de problemas comuns

| Problema | Solução |
|----------|---------|
| `Connection refused` no backend | Verifique se o Docker está aberto e rode `docker compose up -d` |
| `alembic: command not found` | Certifique-se de que o venv está ativo com `.\venv\Scripts\Activate.ps1` |
| Erro `detail: E-mail ou senha incorretos` | Rode `python scripts/run_etl.py` para garantir a criação do usuário coordenador |
| Frontend mostra tela em branco | Abra o console do navegador (F12) para ver o log; certifique-se de que o backend está rodando na porta 8000 |
| Porta `8000` em uso | Inicie o backend em outra porta: `uvicorn main:app --reload --port 8001` (e ajuste a porta no frontend caso necessário) |
| Relatório de inconsistências dos CSVs | Verifique o arquivo gerado em `data/raw/relatorio_excecoes.txt` para checar pré-requisitos não encontrados na matriz |
