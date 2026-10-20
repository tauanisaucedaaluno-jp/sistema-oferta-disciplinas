# Parecer — subir o OfertaPampa para a Natalia

Contexto para continuar o trabalho nesta pasta:
`/home/sam/Documentos/Projetos/sistema-oferta-disciplinas`

Repositório: `https://github.com/tauanisaucedaaluno-jp/sistema-oferta-disciplinas.git`
Branch: `main`, alinhada com `origin/main` em 13/10/2026.

Este arquivo é só um briefing local. Não deve ser commitado.

## Como trabalhar

- Samuel revisa cada alteração antes de ela seguir.
- Não fazer commit nem push. Só entregar a mensagem de commit, no nome dele, sem trailer `Co-authored-by` e sem se incluir como colaborador no GitHub.
- Um passo de cada vez. Depois de cada passo, anotar o que ainda falta.
- Mudança mínima. Não acrescentar serviço, tela ou documentação que o pedido não exija.
- Contas, chaves e cliques na Render e na Vercel são do Samuel. O assistente orienta; não cria projeto na nuvem.

## O que o sistema é

Painel para a coordenação estimar demanda de disciplinas a partir de PPCs e históricos em CSV. Não substitui o SIEPE.

Stack já decidida no ADR 0004: FastAPI + PostgreSQL + React. Login próprio (e-mail e senha, JWT). SSO da UNIPAMPA está fora do MVP.

Três processos:

- Frontend React/Vite em `src/frontend`. Já tem `vercel.json` e lê a API por `VITE_API_URL`.
- Backend FastAPI em `src/backend`. CORS já aceita `https://*.vercel.app`.
- Postgres 16 local só no `docker-compose.yml`. Não há Dockerfile da aplicação.

O ADR 0004 registra um único usuário simultâneo: a coordenadora acadêmica, Natalia Braun Chagas. O código também isola semestres por `usuario_id`, mas isso não será desmontado. A porta de cadastro é que fica fechada em produção.

Supabase não aparece na documentação nem no código. Não usar Supabase Auth nem Google OAuth. Supabase só como Postgres também foi descartado: soma outra conta sem ganho. Frontend na Vercel. API e Postgres na Render.

## O que já está no GitHub

Três commits locais, já enviados para `origin/main`:

1. `fddc414` — `fix: importa Optional para a API iniciar` (`src/backend/api/demanda.py`)
2. `0886d41` — `fix: declara pandas e openpyxl usados na importação` (`src/backend/requirements.txt`)
3. `c63a68a` — `feat: restringe cadastro e login aos e-mails de ALLOWED_EMAILS`

A allowlist funciona assim:

- Variável `ALLOWED_EMAILS` no backend, lista separada por vírgula.
- Vazia: desenvolvimento continua aberto. Não preencher no `.env` local.
- Preenchida: `cadastrar`, `solicitar-acesso` e `login` recusam qualquer outro e-mail com 403 e a mensagem "Este e-mail não está autorizado a acessar o sistema."
- O e-mail é comparado sem diferenciar maiúsculas. O cadastro grava em minúsculas.
- A aba Cadastrar da tela de login permanece. Não foi criada tela nova.
- Testes do backend: 23 passaram na máquina, com `DATABASE_URL` apontando para um SQLite temporário.

Dois ajustes entraram porque, sem eles, a API não sobe: o import de `Optional` em `demanda.py`, e `pandas`/`openpyxl` descomentados no `requirements.txt` (a importação de planilha carrega os dois na inicialização).

## Próximo passo: Render

Só começar depois de confirmar que `git status` está limpo e `main` está igual a `origin/main`. Isso já estava assim no fim desta conversa.

1. Criar um PostgreSQL na Render. Copiar a Internal Database URL (`postgres://...`). O `src/backend/db/database.py` já troca `postgres://` por `postgresql://`.
2. Criar um Web Service a partir deste repositório, branch `main`.
   - Root Directory: `src/backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Variáveis de ambiente do Web Service:
   - `DATABASE_URL`: a URL interna do Postgres
   - `SECRET_KEY`: chave nova, `python3 -c "import secrets; print(secrets.token_hex(32))"`
   - `ALLOWED_EMAILS`: e-mail institucional da Natalia, confirmado com a equipe. Sem isso o cadastro público continua aberto.
   - `FRONTEND_URL`: pode ficar `http://localhost:5173` até existir a URL da Vercel
4. Não rodar Alembic nesse banco novo. O `create_all` em `src/backend/main.py` cria as tabelas na subida. A migração inicial, rodada depois, tentaria criá-las de novo.
5. Abrir `https://<serviço>.onrender.com/health`. Resposta esperada: `{"status":"ok"}`. No plano gratuito o serviço dorme e a primeira abertura demora.

## Depois: Vercel

1. Importar o mesmo repositório.
2. Root Directory: `src/frontend`. Framework Vite. O `src/frontend/vercel.json` já devolve `index.html`.
3. Variável `VITE_API_URL`: URL pública do Web Service, sem barra no final.
4. Anotar a URL `*.vercel.app`.
5. Na Render, atualizar `FRONTEND_URL` para essa URL. O CORS de `*.vercel.app` já está liberado; a variável entra nos links de definição de senha.

## Acesso da Natalia e os dados

Com o site no ar, ela usa a aba Cadastrar, o e-mail que está em `ALLOWED_EMAILS` e uma senha de pelo menos 6 caracteres. O cadastro já abre o painel. Outro e-mail é recusado.

O banco de produção nasce vazio. Os CSV reais não estão no Git (LGPD, RNF02) e não devem ser commitados. No painel, o botão Importar Dados envia CSV/Excel para `POST /importacao/upload`. Sem essa carga ela entra e vê o painel sem históricos. Quem faz o upload é decisão da equipe.

O e-mail exato da Natalia ainda não foi informado nesta conversa. Não inventar.

## O que não fazer agora

- Não trocar o login por Google ou Supabase.
- Não esconder a aba de cadastro.
- Não mexer no motor de demanda nem no schema.
- Não “consertar” o bloqueio de senha em memória nem o sono do plano gratuito da Render. Para uma coordenadora, isso fica aceitável.
