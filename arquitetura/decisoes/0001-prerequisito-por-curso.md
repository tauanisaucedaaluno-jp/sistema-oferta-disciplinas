# ADR 0001 — Pré-requisito é definido por (curso, disciplina), não por disciplina isolada

**Status:** Aceito
**Data:** 12/08/2026
**Relacionado a:** RN01 (`docs/02-regras-de-negocio/regras-de-negocio.md`)

## Contexto

O desenho inicial do sistema modelava pré-requisito como uma propriedade
da disciplina em si — por exemplo, "Cálculo 3 exige Cálculo 2". Essa
modelagem se mostrou incorreta assim que se considerou que uma mesma
disciplina pode ser ofertada a múltiplos cursos.

Confirmado nos dados reais do currículo (`4284_Currículo_Cursos.csv`):
Cálculo III (`AL0020`) é `Obrigatória` em Engenharia Elétrica, Mecânica e
Telecomunicações, mas `Optativa` em Engenharia Civil e `Disciplina
Complementar de Graduação` em Ciência da Computação — com listas de
pré-requisitos diferentes em cada curso.

Se o sistema tratasse pré-requisito como propriedade da disciplina
isolada, ele aplicaria a mesma regra de aptidão a alunos de cursos
diferentes, gerando Grupos B e C incorretos para qualquer disciplina
compartilhada entre cursos.

## Decisão

Pré-requisito é modelado como uma propriedade do **vínculo curricular**
— a combinação `(curso, disciplina)` — e não da disciplina isolada.

Toda consulta do motor de regras (Grupos A, B, C) é executada por par
`(curso, disciplina)`. Quando uma disciplina é compartilhada por vários
cursos, a demanda total é a soma dos resultados calculados
independentemente para cada curso, cada um com sua própria regra de
pré-requisito.

## Consequências

**Positivas:**
- O cálculo de aptidão (Grupo B) e de potencial (Grupo C) reflete
  corretamente a matriz curricular real de cada curso.
- A demanda desagregada por curso (necessária desde que a coordenadora
  pediu esse detalhamento) é uma consequência natural do modelo, não uma
  funcionalidade extra.

**Negativas / custos:**
- O schema não pode ter uma tabela simples `DISCIPLINA → pré-requisitos`;
  precisa de uma tabela de vínculo curricular por curso (ver
  `PRE_REQUISITO` em `docs/04-arquitetura/system-design.md`, Seção 6).
- Toda consulta do motor de regras precisa incluir o curso como parte da
  chave — não é opcional nem um filtro posterior.

## Alternativas consideradas

- **Pré-requisito como propriedade única da disciplina, com exceções por
  curso tratadas como casos especiais:** descartada por gerar lógica
  condicional espalhada pelo código em vez de um modelo de dados
  consistente, e por não refletir como o PPC real está estruturado (o
  próprio CSV de currículo já traz uma linha por curso × disciplina).
