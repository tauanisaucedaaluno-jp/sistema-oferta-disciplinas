# Issues de Desenvolvimento: Sistema de Oferta de Disciplinas

> **Status:** As issues dos épicos 0–6 foram **CONCLUÍDAS**. O projeto está em fase de ajustes finais após revisão da coordenadora. O Epic 7 abaixo lista as novas issues abertas dessa revisão.

Com base no `GUIA-DE-IMPLEMENTACAO.md`, aqui estão as issues detalhadas para o desenvolvimento do projeto, divididas por épicos.

---

## Epic 7 — Ajustes pós-revisão da Coordenadora

### #32 Probabilidade de reprovação no Grupo A (RN10) ✅
**Solicitante:** Coordenadora Natalia — revisão final (2026/2).
**Descrição:** O Grupo A estava sendo somado à demanda como contagem bruta (assumindo que todos os alunos cursando agora iriam reprovar). A coordenadora apontou que isso superestima a demanda — alunos aprovados não precisam da disciplina no próximo semestre.
**O que foi feito:**
- Adicionada a regra de negócio **RN10** em `docs/regras-de-negocio.md`.
- Criado o dataclass `AlunoGrupoA` (espelho de `AlunoGrupoC`) com o campo `probabilidade_reprovacao`.
- Atualizada a função `grupo_a()` em `src/backend/core/groups.py` para retornar `List[AlunoGrupoA]` em vez de `List[str]`.
- Atualizada a fórmula `demanda_estimada()` para somar `probabilidade_reprovacao` por aluno do Grupo A.
- A probabilidade é calculada como `1 - probabilidade_aprovacao_nivel1()` (taxa histórica da disciplina), reutilizando a mesma função já existente para o Grupo C.

**Pendente:** Atualizar a tela de detalhe no frontend (`Detalhe.tsx`) para exibir a `probabilidade_reprovacao` de cada aluno do Grupo A, assim como o Grupo C já exibe.
**Arquivos modificados:**
- [MODIFY] `src/backend/core/groups.py`
- [MODIFY] `docs/regras-de-negocio.md`

---


## Epic 0 — Ambiente de Desenvolvimento

### #1 Configurar backend Python
**Descrição**: Configurar o ambiente inicial para o backend, garantindo que as dependências estejam mapeadas e o servidor rode.
**O que deve ser feito**: 
- Configurar ambiente virtual (venv).
- Criar o `requirements.txt` básico (FastAPI, Uvicorn, SQLAlchemy, psycopg2-binary, etc).
- Criar o arquivo `.env` para as variáveis de ambiente (URL do banco).
- Testar o `main.py` existente executando `uvicorn main:app --reload` e validando a rota `/health`.
**Arquivos a modificar/criar**: 
- [NEW] `requirements.txt`
- [NEW] `.env` e `.env.example`
- [MODIFY] `src/backend/main.py`

### #2 Configurar Postgres local
**Descrição**: Ter uma instância local do Postgres rodando para o desenvolvimento.
**O que deve ser feito**: 
- Criar ou ajustar o `docker-compose.yml` para levantar o banco de dados.
- Garantir que seja possível conectar nele via `psql` ou DBeaver usando as credenciais definidas.
**Arquivos a modificar/criar**: 
- [MODIFY] `docker-compose.yml`

### #3 Configurar Alembic e gerar a migração inicial
**Descrição**: Inicializar a ferramenta de migração de banco de dados e aplicar o schema já definido.
**O que deve ser feito**: 
- Rodar `alembic init` para criar a estrutura do Alembic.
- Configurar o `alembic/env.py` para carregar os metadados do `src/backend/db/models.py`.
- Gerar a primeira migração (`alembic revision --autogenerate -m "Initial schema"`) e aplicá-la.
**Arquivos a modificar/criar**: 
- [NEW] `alembic.ini`
- [NEW] `alembic/env.py` e pasta `alembic/versions/`
- [MODIFY] `src/backend/db/models.py` (se necessário para ajustes no metadata)

### #4 Criar projeto React (Vite)
**Descrição**: Iniciar o esqueleto do frontend e conectar com a API (Hello World).
**O que deve ser feito**: 
- Executar `npm create vite@latest frontend -- --template react-ts` (ou equivalente) dentro de `src/`.
- Criar uma tela única "Hello World" que faz um `fetch` para `/health` da API.
- Confirmar que o frontend e backend conversam (validando CORS).
**Arquivos a modificar/criar**: 
- [NEW] Pasta `src/frontend/` (package.json, src/App.tsx, etc.)
- [MODIFY] `src/backend/main.py` (para conferir configurações de CORS, se necessário)

---

## Epic 1 — Banco de Dados

### #5 Revisar `db/models.py` contra o schema documentado
**Descrição**: Garantir consistência absoluta entre código e arquitetura.
**O que deve ser feito**: 
- Validar se todas as colunas e relações de `db/models.py` estão iguais ao detalhado na Seção 6 do `system-design.md`.
**Arquivos a modificar/criar**: 
- [MODIFY] `src/backend/db/models.py`
- [MODIFY] `arquitetura/system-design.md` (se precisar ajustar alguma inconsistência na doc)

### #6 Registrar formalmente a tabela `usuario`
**Descrição**: A tabela de `usuario` não estava no ER original, mas foi criada para atender ao RF13. Precisamos registrar.
**O que deve ser feito**: 
- Atualizar a Seção 6 do `system-design.md` incluindo as tabelas `usuario` e `log_acesso`.
- Opcionalmente criar um ADR detalhando o motivo.
**Arquivos a modificar/criar**: 
- [MODIFY] `arquitetura/system-design.md`
- [NEW] `arquitetura/decisoes/0005-tabela-usuario-auditoria.md` (opcional)

### #7 Popular `data/sample/` com dados fictícios
**Descrição**: Criar dados falsos para testar o sistema sem depender dos CSVs reais atrasados.
**O que deve ser feito**: 
- Criar um script (SQL ou Python) que insira dados sintéticos no banco cobrindo cenários complexos (disciplinas com códigos diferentes, alunos em vários estados).
**Arquivos a modificar/criar**: 
- [NEW] `data/sample/seed.sql` ou `scripts/seed_db.py`

---

## Epic 2 — ETL de Importação

### #8 Parser de currículo (RF01)
**Descrição**: Ler e processar o currículo enviado pela universidade.
**O que deve ser feito**: 
- Implementar a função para ler o CSV considerando delimitador e encoding (`latin-1`, `;`).
- Deduplicar versões de PPCs considerando a versão mais recente/corrente.
**Arquivos a modificar/criar**: 
- [MODIFY] `etl/importar_curriculo.py`

### #9 Parser de histórico (RF02)
**Descrição**: Ler e processar os registros acadêmicos dos alunos.
**O que deve ser feito**: 
- Implementar a função de leitura para aceitar CSV (e possivelmente XLSX, se demandado).
**Arquivos a modificar/criar**: 
- [MODIFY] `etl/importar_historico.py`

### #10 Normalização de situação (RF03, RN04)
**Descrição**: Padronizar os status da disciplina.
**O que deve ser feito**: 
- Implementar a função de mapeamento (`normalizar_situacao`) das 17 variações reais para os 5 estados canônicos (aprovado, reprovado, cursando, trancado, indefinido).
**Arquivos a modificar/criar**: 
- [NEW] `etl/utils.py` ou `etl/transformacoes.py` (ou dentro dos scripts existentes)

### #11 Construção de CONCEITO_DISCIPLINA (RF04, RN06, ADR 0003)
**Descrição**: O algoritmo de agrupamento de disciplinas equivalentes.
**O que deve ser feito**: 
- Implementar agrupamento por `nome_disciplina` (normalizado) e por `equivalencias` diretas (não-transitivas).
**Arquivos a modificar/criar**: 
- [MODIFY] `etl/importar_curriculo.py` ou [NEW] `etl/conceitos.py`

### #12 Resolução de histórico por conceito (RF04.1, RN06.1)
**Descrição**: Garantir o mapeamento do código bruto cursado para o seu conceito no banco.
**O que deve ser feito**: 
- Ajustar a inserção no banco para garantir que o código bruto cursado pelo aluno não se perca, mas que a vinculação ao conceito se dê via tabela de tradução.
**Arquivos a modificar/criar**: 
- [MODIFY] `etl/importar_historico.py`

### #13 Inferência de periodicidade (RN03)
**Descrição**: Deduzir em qual semestre uma disciplina costuma ser ofertada baseada no histórico.
**O que deve ser feito**: 
- Escrever rotina que avalia as aparições da disciplina nos semestres "1" e "2" ao longo dos anos para inferir: ímpar, par ou ambos.
**Arquivos a modificar/criar**: 
- [MODIFY] `etl/importar_historico.py` (durante consolidação)

### #14 Exclusão de evadidos (RN05)
**Descrição**: Limpar dados que não são alvo do sistema.
**O que deve ser feito**: 
- Identificar e desconsiderar registros de alunos que evadiram do curso.
**Arquivos a modificar/criar**: 
- [MODIFY] `etl/importar_historico.py`

### #15 Relatório de exceções (RF05, RNF07)
**Descrição**: Lidar com inconsistências de dados.
**O que deve ser feito**: 
- Consolidar pré-requisitos não encontrados, códigos não mapeados e outras anomalias em um arquivo para revisão humana.
**Arquivos a modificar/criar**: 
- [NEW] `etl/report.py`

---

## Epic 3 — Motor de Regras

### #16 Taxa histórica de aprovação - Nível 1 (RN09)
**Descrição**: Completar o cálculo da demanda do Grupo C (potenciais).
**O que deve ser feito**: 
- Substituir o `NotImplementedError` em `probabilidade_aprovacao_nivel1` pela lógica matemática correta.
**Arquivos a modificar/criar**: 
- [MODIFY] `src/backend/core/groups.py`

### #17 Testes do Grupo A/B/C
**Descrição**: Validar lógica de negócio do cálculo da demanda.
**O que deve ser feito**: 
- Escrever testes automatizados validando o cálculo de demanda em cima dos dados sintéticos da issue #7.
**Arquivos a modificar/criar**: 
- [NEW] `tests/test_groups.py`

### #18 Suporte a pré-requisitos alternativos (RN07)
**Descrição**: Melhorar modelo de banco para aceitar cláusulas `OU`.
**O que deve ser feito**: 
- Criar ADR discutindo a modelagem.
- Adicionar nova coluna em `pre_requisito` (ex: `grupo_ou`).
- Ajustar lógica em `core/groups.py` para processar opções múltiplas.
**Arquivos a modificar/criar**: 
- [NEW] `arquitetura/decisoes/0006-pre-requisitos-alternativos.md`
- [MODIFY] `src/backend/db/models.py`
- [MODIFY] `src/backend/core/groups.py`

### #19 Seleção de disciplinas candidatas (RF06.1)
**Descrição**: Encontrar discrepâncias de oferta.
**O que deve ser feito**: 
- Criar função para retornar disciplinas que deveriam ser ofertadas no semestre Y mas cuja periodicidade difere.
**Arquivos a modificar/criar**: 
- [NEW/MODIFY] `src/backend/core/resolvers.py` ou novo `src/backend/core/candidatas.py`

---

## Epic 4 — API

### #20 Autenticação (RF13, RNF01, RNF03, RNF04)
**Descrição**: Segurança da aplicação.
**O que deve ser feito**: 
- Implementar geração de token JWT.
- Configurar rotas de login com proteção de hash de senha (passlib).
- Implementar limitação de tentativas.
**Arquivos a modificar/criar**: 
- [NEW] `src/backend/api/auth.py`
- [NEW] `src/backend/core/security.py`
- [MODIFY] `src/backend/main.py`

### #21 Endpoint de demanda (RF06, RF14, RF15)
**Descrição**: Expor os dados do motor de regras.
**O que deve ser feito**: 
- Implementar rotas GET para trazer tamanho dos Grupos A, B, C e Demanda total.
**Arquivos a modificar/criar**: 
- [NEW] `src/backend/api/demanda.py`
- [MODIFY] `src/backend/main.py`

### #22 Filtros por curso/disciplina (RF16)
**Descrição**: Buscas refinadas.
**O que deve ser feito**: 
- Adicionar `Query Parameters` no FastAPI para listar dados passando cursos e conceitos como filtro.
**Arquivos a modificar/criar**: 
- [MODIFY] `src/backend/api/demanda.py`

### #23 Exportação CSV (RF17)
**Descrição**: Exportar relatório.
**O que deve ser feito**: 
- Criar rota `GET /demanda/exportar` que retorne arquivo `.csv` utilizando `StreamingResponse` ou arquivo físico gerado na hora.
**Arquivos a modificar/criar**: 
- [MODIFY] `src/backend/api/demanda.py`

### #24 Log de auditoria (RNF05)
**Descrição**: Rastrear ações dos gestores.
**O que deve ser feito**: 
- Implementar dependência no FastAPI (`Depends`) que insira registros na tabela `log_acesso` a cada ação administrativa.
**Arquivos a modificar/criar**: 
- [NEW] `src/backend/api/deps.py` (ou onde ficarão as dependências)

---

## Epic 5 — Frontend

### #25 Tela de login
**Descrição**: Permitir entrada na plataforma.
**O que deve ser feito**: 
- Interface simples de formulário integrada com a API `/auth/login` salvando o JWT no LocalStorage.
**Arquivos a modificar/criar**: 
- [NEW] `src/frontend/src/pages/Login.tsx`

### #26 Tela de listagem/filtro de disciplinas candidatas
**Descrição**: Visão macro para o coordenador.
**O que deve ser feito**: 
- Tabela ou Grid de componentes mostrando as disciplinas.
- Inputs para filtrar por curso/semestre.
**Arquivos a modificar/criar**: 
- [NEW] `src/frontend/src/pages/Listagem.tsx`

### #27 Tela de detalhe (RF12)
**Descrição**: Visão específica da disciplina.
**O que deve ser feito**: 
- Exibição das métricas quebradas: Grupo A, B, C e estimativa final, além de separar por curso quando houver compartilhamento.
**Arquivos a modificar/criar**: 
- [NEW] `src/frontend/src/pages/Detalhe.tsx`

### #28 Exportação a partir do painel
**Descrição**: Acionar a exportação via interface.
**O que deve ser feito**: 
- Adicionar um botão nas telas pertinentes chamando o endpoint de exportação.
**Arquivos a modificar/criar**: 
- [MODIFY] `src/frontend/src/pages/Listagem.tsx` e `Detalhe.tsx`

---

## Epic 6 — Qualidade e Documentação

### #29 Testes automatizados do motor de regras
**Descrição**: Garantir confiabilidade no cálculo de demanda.
**O que deve ser feito**: 
- Expandir testes com pytest seguindo o TDD mapeado na skill.
**Arquivos a modificar/criar**: 
- [NEW] Diretório `tests/` inteiro.

### #30 Atualizar `docs/COMO-RODAR.md`
**Descrição**: Manter guia prático funcional.
**O que deve ser feito**: 
- A cada nova dependência (ex: migrações de banco, subida do front), o README deve refletir os comandos exatos.
**Arquivos a modificar/criar**: 
- [MODIFY] `docs/COMO-RODAR.md`

### #31 Revisar "Perguntas em aberto" do system-design
**Descrição**: Finalizar definições ambíguas.
**O que deve ser feito**: 
- Responder as questões abertas na Seção 10 em conjunto com a coordenação.
**Arquivos a modificar/criar**: 
- [MODIFY] `arquitetura/system-design.md`
