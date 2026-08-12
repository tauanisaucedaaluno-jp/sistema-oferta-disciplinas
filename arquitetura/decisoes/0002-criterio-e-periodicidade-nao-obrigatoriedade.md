# ADR 0002 — Critério de seleção é periodicidade de oferta, não obrigatoriedade

**Status:** Aceito
**Data:** 12/08/2026
**Relacionado a:** RN02, RN03 (`docs/regras-de-negocio/regras-de-negocio.md`)

## Contexto

A primeira descrição do problema (anotações originais do usuário) definia
o objetivo do sistema como "decidir quais disciplinas ofertar em
semestres pares que não sejam disciplinas obrigatórias". Uma leitura
inicial interpretou isso como um filtro por **tipo de disciplina**
(obrigatória vs. optativa/eletiva).

Essa interpretação foi corrigida pelo usuário: o critério real não é a
obrigatoriedade da disciplina, e sim se ela é **normalmente ofertada
apenas em determinado semestre** (ex.: Cálculo 3, disciplina obrigatória,
ofertada regularmente só em semestres ímpares). A dúvida da coordenação é
se vale abrir uma oferta extraordinária fora desse padrão — não se a
disciplina é obrigatória ou não.

Adicionalmente, os dados reais do currículo confirmaram que o campo
`tipo_disciplina` (`Obrigatória`/`Optativa`/`Disciplina Complementar de
Graduação`/etc.) existe e varia por curso — mas não é o campo relevante
para essa decisão.

## Decisão

O critério de seleção de disciplinas candidatas à análise é a
**periodicidade regular de oferta** (ímpar/par/ambos), não o
`tipo_disciplina`. Uma disciplina obrigatória é candidata legítima de
análise se sua periodicidade regular divergir do semestre avaliado.

Como o PPC não tem campo explícito de periodicidade, ela é **inferida a
partir do histórico de matrículas**: se uma disciplina, por curso, só
aparece com alunos matriculados em `1. Semestre` ao longo dos anos
observados, sua periodicidade é ímpar; se só em `2. Semestre`, é par; se
aparece nos dois, é "ambos" e fica fora do escopo de análise (já é
ofertada regularmente nos dois semestres).

O sistema evoluiu depois para dois modos de uso (ver RN02 atualizado): o
modo "oferta extraordinária" aplica esse filtro de periodicidade; o modo
"demanda no semestre regular" não aplica — a disciplina é escolhida
manualmente pelo usuário, sem essa restrição.

## Consequências

**Positivas:**
- O sistema responde à pergunta real da coordenação, não a uma
  interpretação plausível porém incorreta dela.
- `tipo_disciplina` continua disponível no modelo de dados (é um dado real
  do PPC) para uso futuro (ex.: exibição informativa), mas não participa
  da lógica de seleção.

**Negativas / custos:**
- A periodicidade de oferta não é um dado direto — precisa ser calculada
  no ETL a partir do histórico, o que a torna dependente da qualidade e
  completude desse histórico (uma disciplina nova, sem histórico
  suficiente, não tem periodicidade inferível).
- Se uma disciplina mudar de padrão de oferta ao longo do tempo (por
  decisão futura da própria coordenação), a inferência histórica pode
  ficar desatualizada — não há mecanismo de override manual definido
  ainda.

## Alternativas consideradas

- **Filtrar por `tipo_disciplina` (obrigatória/optativa):** era a
  interpretação inicial; descartada porque não corresponde à necessidade
  real relatada pela coordenação.
- **Exigir que a periodicidade venha cadastrada manualmente, em vez de
  inferida:** mais confiável em tese, mas cria dependência de um processo
  manual de cadastro que não existe hoje — inviável para o MVP dado o
  volume de disciplinas envolvido.
