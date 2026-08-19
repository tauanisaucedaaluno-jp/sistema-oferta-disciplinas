# ADR 0004 — Stack técnica: FastAPI (backend), PostgreSQL (banco) e React (frontend)

**Status:** Aceito
**Data:** 19/08/2026
**Relacionado a:** RNF01, RNF03, RNF04, RNF06, RNF08, RNF09 (`docs/requisitos-nao-funcionais.md`)

## Contexto

O system-design (Seção 10) registrava como pendente a definição da stack
técnica do painel de gestão. As restrições que guiaram a decisão foram:

- **Backend obrigatoriamente Python** — decisão já fixada pela equipe,
  compatível com o ETL (pandas) e com o motor de regras já especificados
  em Python.
- **Um único usuário simultâneo** (a coordenadora acadêmica) — sem
  necessidade de escala horizontal, filas ou cache distribuído.
- **Dados chegam por CSV exportado manualmente** — sem integração em tempo
  real com o sistema acadêmico, sem necessidade de workers assíncronos.
- **Equipe com nível técnico intermediário** e rotatividade de bolsistas
  (RNF09) — a stack precisa ser amplamente documentada, com curva de
  aprendizado razoável e sem dependências exóticas.
- **Dados pessoais de alunos (LGPD)** — autenticação e controle de acesso
  são requisitos funcionais (RF13), não opcionais.
- **Arquitetura monolítica simples (cliente–servidor local)** — escolha
  deliberada para o MVP dado o perfil de uso; microsserviços ou
  contêineres orquestrados adicionariam complexidade sem benefício real.

## Decisão

Adotar a seguinte stack:

**Backend — FastAPI (Python)**
Framework web moderno, tipado, com geração automática de documentação
interativa (Swagger UI / ReDoc). Escolhido sobre Flask por oferecer
validação de dados via Pydantic embutida, suporte nativo a tipagem estática
(reduz bugs no motor de regras e no ETL) e documentação de endpoints
gerada automaticamente — útil para onboarding de novos bolsistas.
Bibliotecas complementares: SQLAlchemy (ORM), Alembic (migrations),
python-jose ou similar (JWT para autenticação), passlib (hash de senhas,
RNF01).

**Banco de dados — PostgreSQL**
Banco relacional robusto, sem custo de licença, amplamente documentado e
com suporte nativo a tipos complexos (arrays, JSONB) que podem ser úteis
para armazenar listas de pré-requisitos e equivalências. Escolhido sobre
SQLite porque, embora o volume de usuários simultâneos seja baixo, o
PostgreSQL oferece melhor suporte a consultas analíticas (os cálculos dos
Grupos A/B/C envolvem joins e agregações sobre históricos de alunos de
múltiplos cursos) e integridade referencial mais rigorosa. A migração de
SQLite para PostgreSQL com SQLAlchemy teria custo não desprezível; começar
com PostgreSQL evita essa dívida técnica. Acesso via SQLAlchemy com
Alembic para versionamento do schema.

**Frontend — React**
Biblioteca de UI amplamente adotada, com vasto ecossistema de componentes
e material de aprendizado. Adequada para o painel de gestão (SPA com
formulário de busca, painel de resultado por grupos A/B/C e exportação).
O frontend consome a API REST do backend via HTTP — separação limpa de
responsabilidades que permite que backend e frontend sejam desenvolvidos
e testados independentemente.

## Consequências

**Positivas:**
- FastAPI gera documentação interativa automaticamente — novos bolsistas
  conseguem explorar os endpoints sem precisar ler o código.
- SQLAlchemy + Alembic permitem evoluir o schema do banco (Seção 6 do
  system-design tem pendências em aberto) sem perder dados.
- A separação backend/frontend via API REST viabiliza, no futuro, um
  cliente diferente (ex.: CLI, exportação automatizada) sem mudar o
  backend.
- React tem comunidade e documentação amplas — compatível com o perfil
  de equipe intermediária com rotatividade.

**Negativas / custos:**
- PostgreSQL requer um servidor de banco em execução localmente (vs.
  SQLite, que é um arquivo). Para desenvolvimento local, o uso de Docker
  ou de uma instalação direta do PostgreSQL é necessário — adiciona um
  passo de setup que deve ser documentado no README.
- React implica um processo de build separado (npm/vite) — a equipe
  precisa manter dois ambientes de desenvolvimento (Python e Node.js).
  Para o MVP, isso é administrável; deve ser documentado no README junto
  com as instruções de execução.
- A autenticação própria (login/senha, RF13) precisa ser implementada
  — não há integração com SSO/LDAP da UNIPAMPA no MVP (registrado como
  fora de escopo na Seção 9 do system-design). A política de senhas e
  recuperação de acesso ainda está em aberto (Seção 10 do system-design).

## Alternativas consideradas

- **Flask (backend):** mais simples e amplamente conhecido, mas sem
  validação de dados embutida e sem documentação automática de endpoints.
  Descartado em favor do FastAPI dado o benefício de onboarding para
  novos bolsistas e a tipagem que ajuda a manter o motor de regras
  correto.
- **SQLite (banco):** zero configuração, arquivo único — ideal para
  protótipos. Descartado por limitações em consultas analíticas intensas
  e pela dificuldade de migrar depois, uma vez que o schema envolve
  entidades com muitos relacionamentos (CONCEITO_DISCIPLINA, PRE_REQUISITO,
  HISTORICO — ver Seção 6 do system-design).
- **Vue (frontend):** curva de aprendizado mais suave que React, sintaxe
  mais próxima de HTML. Considerado como alternativa equivalente para
  este projeto — a escolha por React foi de preferência da equipe, não
  por superioridade técnica objetiva para este caso de uso.
- **Renderização server-side (ex.: Django + templates HTML):** eliminaria
  a necessidade de manter dois ambientes (Python + Node.js). Descartado
  porque a equipe já tem familiaridade com React e a separação via API
  REST é mais flexível para iterações futuras no painel.
