# Guia de Implementação — Sistema de Oferta de Disciplinas

> Este guia é o elo entre a documentação de decisão que vocês já têm
> (`docs/`, `arquitetura/`) e código rodando. Ele não substitui os
> documentos existentes — refere-se a eles o tempo todo. Leia isto uma vez
> do início ao fim antes de abrir o editor de código.

## 1. Diagnóstico: o que já existe, o que faltava

Vocês já fizeram a parte mais difícil de um projeto como este: entender o
problema. Isso está registrado em:

- `docs/requisitos-funcionais.md` e `requisitos-nao-funcionais.md` — o
  "o quê" (RF01–RF17, RNF01–RNF11).
- `docs/regras-de-negocio.md` — o "como calcular" (RN01–RN09), com casos
  reais de dados que já invalidaram abordagens ingênuas (isso é ouro —
  muitos projetos descobrem esses problemas só em produção).
- `arquitetura/decisoes/000X-*.md` (ADRs) — decisões já tomadas e por quê,
  incluindo alternativas descartadas.
- `arquitetura/system-design.md` — como as peças se encaixam.

O que faltava era só a parte de execução: as pastas `src/`, `etl/`
existiam vazias (só com `__init__.py`, e com erro de digitação —
`__inity__.py` — que eu já corrigi, porque esse nome exato é exigido pelo
Python para reconhecer uma pasta como pacote). Eu adicionei um esqueleto
de código funcional dentro dessa estrutura — não é o sistema completo,
mas é o suficiente para vocês rodarem algo real desde o primeiro dia e
para eu (ou qualquer bolsista novo) continuar a partir de um ponto sólido.

### O que eu já implementei de verdade (roda, não é só esqueleto)

- `src/backend/db/models.py` — todas as tabelas do schema (Seção 6 do
  system-design), incluindo uma tabela `usuario` que faltava para RF13
  (autenticação) e não estava no diagrama ER original — sinalizei isso
  no próprio arquivo como algo a registrar formalmente (ver Issue 6).
- `src/backend/db/database.py` — conexão com o Postgres.
- `src/backend/core/resolvers.py` — a função `resolver_conceito()`, que é
  o coração de todo o sistema (explico por quê na Seção 4 abaixo).
- `src/backend/core/groups.py` — Grupos A, B, C e cálculo de demanda,
  **implementados de verdade** contra o schema (não são pseudo-código),
  exceto a taxa de aprovação (RN09) que deixei como `NotImplementedError`
  de propósito — calcular isso direito exige olhar dados reais primeiro
  para não errar a fórmula silenciosamente.
- `src/backend/main.py` — API FastAPI que já sobe (`/health` funciona).
- `docker-compose.yml` — Postgres local com um comando.

### O que ficou como esqueleto (funções com `NotImplementedError`)

- `etl/importar_curriculo.py` e `etl/importar_historico.py` — as
  assinaturas de função e a ordem certa de chamá-las já estão prontas,
  com comentário explicando o que cada uma precisa fazer e citando a
  regra de negócio correspondente. O corpo depende dos CSVs reais — é
  onde eu preciso dos arquivos que você vai me mandar.

---

## 2. Ordem de implementação — por que essa ordem

Não dá para implementar o motor de regras sem o schema do banco. Não dá
para testar o ETL sem saber o formato real dos CSVs. A ordem que faz
sentido é:

```
1. Ambiente (Postgres + FastAPI + React "hello world")   ← já pode começar hoje
2. Banco de dados (schema + migrations)                   ← já pode começar hoje
3. ETL (currículo + histórico)                             ← precisa dos CSVs reais
4. Motor de regras (Grupos A/B/C + demanda)                ← precisa do banco populado (passo 3)
5. API (endpoints que expõem o motor de regras)             ← precisa do passo 4
6. Frontend (painel de gestão)                              ← precisa do passo 5
7. Autenticação e auditoria                                 ← pode ser paralelo, junta no fim
```

Ou seja: **você pode e deve começar agora**, sem esperar os CSVs, nos
passos 1 e 2. Assim que eu tiver os CSVs (ou uma amostra representativa
deles), a gente destrava o passo 3 e o resto flui.

---

## 3. Como rodar o que já existe

Ver `docs/COMO-RODAR.md` — passo a passo de Docker, backend e frontend.
Resumo: `docker compose up -d` sobe o banco, `uvicorn main:app --reload`
sobe a API.

---

## 4. O banco de dados, explicado (não só o schema — o *porquê*)

O ponto mais não-óbvio do projeto inteiro é este, então vale reforçar em
palavras simples, mesmo que já esteja no ADR 0003:

**Problema:** o código de uma disciplina no sistema acadêmico não é fixo.
"Cálculo I" já foi `AL0001`, depois `AL0363`, depois `DAL2002` — códigos
diferentes, mesma disciplina, ao longo de reformas curriculares. Pior:
não dá para adivinhar qual código um aluno usou olhando a versão do PPC
dele — os dados reais mostraram alunos "antigos" com código novo e
alunos "novos" com código antigo, misturados no mesmo semestre.

**Por que isso importa pro sistema:** se o sistema perguntar "este aluno
já foi aprovado em Cálculo I?" comparando só o código exato, ele vai
errar — vai dizer que não, porque o aluno foi aprovado sob um código
diferente do que está sendo comparado.

**A solução (`CONCEITO_DISCIPLINA`):** criar uma "identidade" que
represente "Cálculo I" independente do código usado. Toda vez que o
sistema precisa comparar disciplinas (para checar pré-requisito, por
exemplo), ele primeiro traduz o código bruto para esse conceito — usando
a tabela `CODIGO_DISCIPLINA`, que é só uma tabela de tradução:
`("AL0001", "curso X") → conceito "Cálculo I do curso X"`. Isso é
literalmente o que a função `resolver_conceito()` faz — é uma junção
(JOIN) simples, mas é usada em praticamente toda consulta do sistema.

**As outras tabelas, resumidas:**

| Tabela | O que guarda | Por que existe separada |
|---|---|---|
| `curso` | Nome/código de cada curso | Chave de quase tudo |
| `conceito_disciplina` | A identidade estável de uma disciplina, por curso | Resolve o problema acima |
| `codigo_disciplina` | Cada código bruto já visto → aponta pro conceito | É a "tabela de tradução" |
| `vinculo_curricular` | Periodicidade de oferta e período sugerido, por (curso, conceito) | Um conceito pode ter regras diferentes em cursos diferentes (ADR 0001) |
| `pre_requisito` | Quais conceitos são exigidos para cursar outro conceito, por curso | Um conceito pode ter vários pré-requisitos (relação 1-N) |
| `aluno` | Matrícula, curso | — |
| `historico` | Uma linha por (aluno, disciplina cursada, período), com o código **bruto**, nunca traduzido | O código bruto é preservado para sempre; a tradução acontece na consulta, não na importação (RN06.1) — isso evita perder informação se o mapeamento de conceitos mudar depois |
| `usuario` | Login do painel (**adicionei** — não estava no diagrama original) | RF13 exige autenticação |
| `log_acesso` | Auditoria de quem acessou o quê | RNF05 |

---

## 5. O ETL, explicado como algoritmo (não só como especificação)

O ETL ("Extract, Transform, Load") é o processo que lê os CSVs brutos e
enche essas tabelas. Pensando em passos concretos:

**Passo 1 — Ler e limpar.** Abrir o CSV com o separador e encoding certos
(`;` e `latin-1`, confirmado nos dados reais). Isso vira uma tabela em
memória (um `DataFrame` do pandas).

**Passo 2 — Deduplicar versões de currículo.** O mesmo par (curso,
disciplina) aparece várias vezes no CSV de currículo, uma vez por versão
de PPC. Precisa decidir qual linha é "a atual" — a regra proposta é
`situacao = 'ATIVA'` + versão mais recente, mas o ADR 0003 descobriu que
**mais de uma versão pode estar simultaneamente `ATIVO`** — por isso o
MVP usa a versão marcada `CORRENTE` como a definição vigente. Isso é uma
simplificação assumida conscientemente, não um detalhe esquecido.

**Passo 3 — Construir os conceitos.** Este é o algoritmo mais importante
do ETL:
```
para cada curso:
  agrupar todos os códigos vistos (currículo + histórico) por
  nome_disciplina normalizado (maiúsculo, sem acento, sem espaço duplo)
  → cada grupo vira um CONCEITO_DISCIPLINA

  além disso, se um código A cita um código B no campo `equivalencias`
  DIRETAMENTE (uma linha específica, sem seguir a cadeia adiante),
  juntar A e B no mesmo conceito, mesmo que os nomes sejam diferentes
  (cobre casos de renomeação na reforma curricular)
```
O ADR 0003 já testou a alternativa "óbvia" (seguir `equivalencias` de
forma transitiva, unindo tudo que está conectado por qualquer caminho) e
ela **falhou nos dados reais** — misturou Cálculo, Física e Álgebra
Linear no mesmo grupo. Por isso o algoritmo acima é deliberadamente mais
conservador (só um salto direto, não a cadeia inteira).

**Passo 4 — Inferir periodicidade de oferta.** Não existe no PPC; é
inferida olhando em que semestre (`1. Semestre`/`2. Semestre`) o
conceito teve alunos matriculados, ao longo dos anos, no histórico:
```
para cada (curso, conceito):
  semestres = conjunto de "1" ou "2" em que houve matrícula, por ano
  se só apareceu "1" em todos os anos → periodicidade = ímpar
  se só apareceu "2" em todos os anos → periodicidade = par
  se apareceu nos dois → periodicidade = ambos (fora do escopo de análise)
```

**Passo 5 — Normalizar situação.** Trocar o texto livre do CSV
(`"Aprovado com nota"`, `"Reprovado por Frequência"`, etc.) pelos 5
estados canônicos da tabela RN04 (aprovado / reprovado / cursando /
trancado / indefinido). É uma tabela de tradução direta — sem lógica
complexa, só precisa ser completa (cobrir os 17 valores confirmados).

**Passo 6 — Nunca falhar silenciosamente.** Toda vez que o ETL encontra
algo que não sabe resolver (um código sem conceito conhecido, um
pré-requisito citando disciplina inexistente), ele registra isso numa
lista de exceções em vez de descartar a linha ou travar o processo
inteiro. No fim, essa lista vira o "relatório de exceções" (RF05) — que
alguém humano revisa.

---

## 6. O motor de regras, explicado como algoritmo

Já implementado em `core/groups.py` — aqui vai a versão em português do
que o código faz, com um exemplo:

> Exemplo: avaliando "Cálculo III" no curso de Engenharia Elétrica, para
> o semestre 2026/2. Pré-requisito: Cálculo II.

**Grupo A — matriculados.** Simplesmente: quem, no histórico, tem uma
linha para o conceito "Cálculo III" com `periodo_letivo = 2026/2` e
`situacao = cursando`.

**Grupo B — aptos, não matriculados.** Para cada aluno do curso: ele foi
aprovado em TODOS os pré-requisitos do conceito (aqui, só Cálculo II)? E
ele NÃO está, agora, aprovado ou cursando o próprio Cálculo III? Se as
duas coisas forem verdade, ele conta.

**Grupo C — potenciais.** Para cada aluno do curso: ele está cursando
AGORA algum dos pré-requisitos (Cálculo II, neste exemplo)? Se sim, ele
entra no grupo, com uma probabilidade de aprovação associada — no MVP,
essa probabilidade é sempre a mesma para todo mundo cursando aquele
pré-requisito: a taxa histórica de aprovação dele (RN09, "Nível 1" —
Níveis 2 e 3, mais precisos, ficam fora do MVP de propósito, RN09 e
Seção 9 do system-design).

**Demanda estimada** = |Grupo A| + |Grupo B| + soma das probabilidades
de todo mundo no Grupo C. Não é um número inteiro necessariamente (por
causa da soma de probabilidades) — isso é esperado, é uma estimativa.

**Ponto em aberto que eu sinalizei no código (RN07):** a lista de
pré-requisitos de uma disciplina pode misturar "E" (todos exigidos) com
"OU" (alternativas — se o aluno passou em qualquer um dos dois códigos
listados como equivalentes, conta). O schema atual de `pre_requisito`
não tem uma coluna para marcar "estas duas linhas são um grupo OU, não
duas exigências E". Implementei a versão mais simples (tudo é E) e
documentei isso como uma issue própria — não deve ser resolvido "por
adivinhação" no meio de outra tarefa.

---

## 7. API e Frontend — o que falta desenhar

A API (FastAPI) vai expor o motor de regras via HTTP. Endpoints mínimos
para o MVP, na ordem em que fazem sentido para o painel funcionar:

1. `POST /auth/login` — autenticação (RF13)
2. `GET /disciplinas/candidatas?semestre=2026/2` — lista as disciplinas
   cuja periodicidade diverge do semestre avaliado (RF06.1, modo "oferta
   extraordinária")
3. `GET /demanda?curso=X&conceito=Y&periodo=2026/2` — Grupos A/B/C +
   demanda total para uma disciplina específica (RF06, modo "demanda no
   semestre regular" — sem o filtro de periodicidade)
4. `GET /demanda/exportar?...` — mesmo dado, em CSV (RF17)
5. `POST /importacao` — dispara o ETL a partir de um CSV enviado (pode
   ficar para depois do MVP funcionar via linha de comando — rodar o ETL
   manualmente é aceitável no início)

O frontend (React) precisa de, no mínimo: tela de login, tela de listagem
com filtro por curso/disciplina (RF16), tela de detalhe mostrando Grupos
A/B/C e o total, botão de exportar (RF17). Nada disso precisa ser
sofisticado visualmente no MVP — RNF08 pede que seja usável por um
perfil não técnico, não que seja bonito.

---

## 8. Divisão em Issues

Sugestão de épicos e issues, pensada para: (a) permitir trabalho paralelo
entre os dois bolsistas quando possível, (b) sempre citar o RF/RN/ADR de
origem (convenção já definida em `docs/README.md`), (c) seguir o espírito
de "um teste, uma implementação, por vez" que já está descrito em
`.agents/skills/tdd/SKILL.md` do próprio repositório.

### Epic 0 — Ambiente de desenvolvimento
*Pode começar agora, sem os CSVs.*

- **#1 Configurar backend Python** — venv, `requirements.txt`, `.env`.
  Critério de aceite: `uvicorn main:app --reload` sobe e `/health`
  responde `{"status": "ok"}`.
- **#2 Configurar Postgres local** — `docker compose up -d` sobe o banco
  e é possível conectar nele (ex.: via `psql` ou DBeaver).
- **#3 Configurar Alembic e gerar a migração inicial** a partir de
  `db/models.py`. Critério de aceite: `alembic upgrade head` cria todas
  as tabelas da Seção 6 do system-design (incluindo `usuario` e
  `log_acesso`).
- **#4 Criar projeto React (Vite)** em `src/frontend`, tela única
  "Hello World" consumindo `/health` da API, confirmando que
  frontend e backend conversam (CORS já liberado em `main.py`).

### Epic 1 — Banco de dados
*Pode começar agora.*

- **#5 Revisar `db/models.py` contra o schema documentado** — conferir
  se bate com a Seção 6 do system-design linha a linha; ajustar se algo
  divergir.
- **#6 Registrar formalmente a tabela `usuario`** — atualizar a Seção 6
  do system-design.md (ou abrir um ADR novo) para incluir `usuario` e
  `log_acesso`, já que RNF09 exige que decisões de modelagem sejam
  documentadas, não só implementadas.
- **#7 Popular `data/sample/` com dados fictícios** — um pequeno conjunto
  de cursos/conceitos/alunos/histórico inventado, cobrindo os casos
  interessantes (disciplina compartilhada entre cursos, conceito com
  código variável, aluno em cada um dos 5 estados canônicos). Serve para
  testar o motor de regras sem esperar os CSVs reais.

### Epic 2 — ETL de importação
*Bloqueado até eu receber os CSVs (ou uma amostra representativa e, se possível, anonimizada — ver Seção 9).*

- **#8 Parser de currículo** (RF01) — `ler_csv_curriculo` +
  `deduplicar_versoes`, contra o CSV real.
- **#9 Parser de histórico** (RF02) — `ler_historico`, aceitando CSV e
  XLSX.
- **#10 Normalização de situação** (RF03, RN04) — `normalizar_situacao`.
- **#11 Construção de `CONCEITO_DISCIPLINA`** (RF04, RN06, ADR 0003) —
  a parte mais delicada; recomendo escrever teste primeiro com o caso
  real já documentado (Cálculo I: `AL0001`/`AL0363`/`DAL2002`).
- **#12 Resolução de histórico por conceito** (RF04.1, RN06.1) — garantir
  que nenhuma linha de histórico é descartada ou reescrita.
- **#13 Inferência de periodicidade** (RN03) — `inferir_periodicidade`.
- **#14 Exclusão de evadidos** (RN05) — `excluir_evadidos`.
- **#15 Relatório de exceções** (RF05, RNF07) — consolidar tudo que os
  passos acima não conseguiram resolver.

### Epic 3 — Motor de regras
*Pode ser feito em paralelo ao Epic 2, usando os dados fictícios do Epic 1 (#7) — não precisa esperar os CSVs reais para testar a lógica.*

- **#16 Taxa histórica de aprovação (Nível 1)** (RN09) — implementar o
  `NotImplementedError` deixado em `probabilidade_aprovacao_nivel1`.
- **#17 Testes do Grupo A/B/C** com os dados fictícios de `data/sample/`,
  cobrindo especificamente o caso de disciplina compartilhada com
  pré-requisitos diferentes por curso (ADR 0001).
- **#18 Decidir e implementar suporte a pré-requisitos alternativos**
  (RN07) — inclui uma mudança de schema (nova coluna em `pre_requisito`
  para marcar grupos "OU"); discutir antes de implementar, é uma decisão
  de modelagem (RNF09 pede ADR).
- **#19 Seleção de disciplinas candidatas** (RF06.1) — filtro de
  periodicidade divergente do semestre avaliado.

### Epic 4 — API
- **#20 Autenticação** (RF13, RNF01, RNF03, RNF04) — login com JWT, hash
  de senha com passlib, limite de tentativas, expiração de sessão.
- **#21 Endpoint de demanda** (RF06, RF14, RF15) — os dois modos de
  análise.
- **#22 Filtros por curso/disciplina** (RF16).
- **#23 Exportação CSV** (RF17).
- **#24 Log de auditoria** (RNF05) — registrar em `log_acesso`.

### Epic 5 — Frontend
- **#25 Tela de login.**
- **#26 Tela de listagem/filtro de disciplinas candidatas.**
- **#27 Tela de detalhe** — Grupos A/B/C, demanda total, quebra por curso
  quando compartilhada (RF12).
- **#28 Exportação a partir do painel.**

### Epic 6 — Qualidade e documentação
- **#29 Testes automatizados do motor de regras** — seguindo o workflow
  de TDD já descrito em `.agents/skills/tdd/`.
- **#30 Atualizar `docs/COMO-RODAR.md`** conforme o setup real evoluir.
- **#31 Revisar "Perguntas em aberto" da Seção 10 do system-design** —
  várias dependem de validação com a coordenadora, não são technicamente
  bloqueantes mas precisam ser fechadas antes de considerar o MVP pronto.

---

## 9. Próximo passo

Pode me mandar os CSVs/relatórios de currículo e histórico agora — mesmo
que sejam de um curso só para começar (Ciência da Computação e
Engenharia Civil já foram os cursos usados para validar as regras, então
são um bom ponto de partida se você tiver). Duas coisas importantes:

1. **Dado real de aluno é dado sensível (LGPD)** — RNF02 já deixa isso
   registrado no projeto. Se puder, mande uma amostra com as matrículas
   substituídas por identificadores fake antes de me enviar (mantendo a
   mesma matrícula fake em todas as linhas do mesmo aluno, para não
   quebrar a lógica). Se não der para anonimizar antes, me avise e a
   gente decide juntos o que fazer.
2. Com os CSVs em mãos, eu confirmo os nomes reais de coluna (a Seção 5
   do system-design já avisa que os nomes atuais são hipóteses) e
   implemento de fato as funções de `etl/importar_curriculo.py` e
   `etl/importar_historico.py` — destravando o Epic 2 e, em seguida, a
   Issue #16 do motor de regras.
