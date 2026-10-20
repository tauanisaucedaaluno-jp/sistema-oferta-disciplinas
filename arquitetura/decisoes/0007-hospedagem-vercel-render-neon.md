# ADR 0007 — Hospedagem do MVP: Vercel, Render e Neon

**Status:** Aceito
**Data:** 13/10/2026
**Relacionado a:** ADR 0004, RNF02, RNF09

## Contexto

O ADR 0004 fixou a stack do painel: FastAPI, PostgreSQL e React, com um
único usuário simultâneo (a coordenadora acadêmica) e login próprio por
e-mail e senha. O MVP precisa ficar no ar para essa coordenadora usar o
painel e importar os CSV. A equipe não tem verba para plano mensal.

O banco gratuito da Render apaga os dados. A documentação da plataforma
(consultada em 13/10/2026) estabelece que um Postgres no plano Free expira
30 dias depois da criação, fica inacessível e, após mais 14 dias sem
mudança para um plano pago, é apagado junto com os históricos. O menor
plano pago custa US$ 6 por mês. Isso inviabiliza a Render como lugar dos
dados.

O Web Service gratuito da Render não tem esse prazo. Ele dorme depois de
15 minutos sem requisição e acorda em cerca de um minuto na visita
seguinte. O workspace tem 750 horas gratuitas por mês, contadas só
enquanto o serviço está acordado. Para uma coordenadora, o sono da
primeira abertura é aceitável. O serviço não guarda arquivo entre deploys:
disco persistente existe só em plano pago.

O Neon, no plano Free consultado na mesma data, oferece Postgres sem prazo
de expiração, com 1 GB por projeto e 100 horas de processamento por mês. O
compute dorme após 5 minutos parado e os dados permanecem. Estourar a cota
mensal suspende o compute até o mês seguinte; não apaga o banco. O Neon não
executa aplicação Python.

Subir o Postgres numa máquina da equipe não muda o código: o backend só lê
`DATABASE_URL`, e o `docker-compose.yml` já sobe Postgres 16. Falta a
máquina sempre ligada, o backup e uma rede que aceite visita de fora. A
porta 5432 não pode ficar publicada: o banco guarda matrícula e histórico
(RNF02, LGPD). A Oracle Cloud tem VM Always Free, mas a instância ociosa
por 7 dias (CPU, rede e memória abaixo de 20%) pode ser recolhida, a
criação pode falhar por falta de capacidade, e a operação ficaria com
bolsistas em rotatividade (RNF09).

SQLite dentro da API foi recusado de novo. O ADR 0004 já o tinha deixado de
lado pelas consultas dos grupos A, B e C. No Web Service gratuito da Render
o arquivo se perderia a cada sono ou publicação.

Supabase, mesmo usado só como Postgres, pausa o projeto após cerca de uma
semana de pouco uso. A coordenadora não entra todo dia. Autenticação do
Supabase, do Neon e login com Google ficam de fora: o MVP continua com
e-mail, senha e JWT.

## Decisão

Hospedar o MVP em três serviços, cada um no plano gratuito, sem alterar o
motor de demanda nem o schema:

1. **Frontend na Vercel.** Repositório atual, branch `main`, raiz
   `src/frontend`, framework Vite. A variável `VITE_API_URL` recebe a URL
   pública da API, sem barra no final. O `src/frontend/vercel.json` já
   devolve `index.html`.
2. **API na Render, Web Service gratuito.** Raiz `src/backend`, linguagem
   Python 3, branch `main`, região Ohio (US East). Build:
   `pip install -r requirements.txt`. Start:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`. Não criar o Postgres da
   Render.
3. **Banco no Neon, Postgres 16, plano Free, região AWS US East 2 (Ohio),**
   a mesma da API. O projeto foi criado nessa região. A connection string
   usada em `DATABASE_URL` é a direta:
   o hostname não contém `-pooler`. A API abre uma sessão por requisição; o
   pooler do Neon encerra a sessão no meio do pedido. A string traz a senha
   e não entra no Git.

Variáveis do Web Service:

- `DATABASE_URL`: a connection string direta do Neon
- `SECRET_KEY`: chave nova, gerada na hora do deploy
- `ALLOWED_EMAILS`: e-mail institucional da coordenadora, quando a equipe
  confirmar o endereço. Vazio, o cadastro público continua aberto.
- `FRONTEND_URL`: a URL `*.vercel.app`, sem barra no final. Até essa URL
  existir, pode ficar `http://localhost:5173`. O CORS de `https://*.vercel.app`
  já está liberado no código; a variável entra nos links de definição de
  senha.

Na primeira subida de um banco vazio, as tabelas nascem pelo `create_all`
em `src/backend/main.py`. Não rodar Alembic nesse banco: a migração inicial,
aplicada depois, tentaria criar as tabelas de novo.

Os CSV reais continuam fora do Git (RNF02). A carga é o botão Importar
Dados do painel (`POST /importacao/upload`).

## Consequências

**Positivas:**

- Os históricos não ficam num banco com data marcada para apagar.
- O código do painel permanece o mesmo. Trocar de provedor no futuro é
  mudar `DATABASE_URL`.
- O plano gratuito da API basta para um usuário: o serviço dorme e a hora
  gratuita só é gasta enquanto está acordado.
- Login, allowlist e isolamento por `usuario_id` seguem como já estão no
  código.

**Negativas / custos:**

- Três contas (Vercel, Render, Neon). Nenhuma cobra mensalidade dentro
  destes limites.
- A primeira abertura depois de 15 minutos parado na Render leva cerca de
  um minuto. O Neon acrescenta uma fração de segundo ao acordar.
- 1 GB no Neon. Acima disso, gravações que aumentam o disco falham; o que
  já está armazenado permanece.
- 100 horas de processamento do Neon por mês. Acima disso, o banco para
  até o mês seguinte.
- 750 horas do Web Service por mês, por workspace. Manter a API acordada
  de propósito com acessos periódicos gastaria a cota e suspenderia o
  serviço até o mês seguinte.
- O plano Free do Neon tem janela curta de restauração (6 horas na data
  desta decisão). Backup de longo prazo não faz parte deste MVP.
- O e-mail da coordenadora ainda precisa ser confirmado pela equipe antes
  de preencher `ALLOWED_EMAILS`.

## Alternativas consideradas

- **Postgres gratuito na Render:** descartado porque expira em 30 dias e os
  dados são apagados.
- **Postgres pago na Render (US$ 6/mês):** serve tecnicamente e faz backup.
  Descartado por falta de verba.
- **API e Postgres numa máquina da equipe:** o código não mudaria.
  Descartado porque não há computador sempre ligado, com rede liberada e
  alguém responsável por backup e atualização.
- **VM Always Free na Oracle, com Postgres instalado pela equipe:** sem
  mensalidade, e ainda assim uma conta de terceiro. Descartado pelo risco
  de a instância ociosa ser recolhida e pela operação acima do que a
  rotatividade de bolsistas sustenta.
- **SQLite no processo da API:** descartado pelo ADR 0004 e porque o disco
  do Web Service gratuito não persiste.
- **Supabase só como Postgres:** descartado porque o projeto gratuito pausa
  após cerca de uma semana de pouco uso. Auth do Supabase permanece fora
  do MVP.
- **Levar a API também para o Neon:** impossível. O Neon hospeda o
  Postgres; o FastAPI continua num serviço que executa Python.
