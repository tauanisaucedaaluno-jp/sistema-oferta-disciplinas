# Regras de Negócio

## RN01 — Pré-requisito é definido por (curso, disciplina), não por disciplina isolada

Uma mesma disciplina pode ser ofertada a múltiplos cursos com
pré-requisitos diferentes em cada um. Confirmado nos dados reais: Cálculo
III é `Obrigatória` em Engenharia Elétrica/Mecânica/Telecomunicações e
`Optativa`/`Complementar` em outros cursos, com pré-requisitos distintos.

**Consequência:** todas as consultas do sistema (Grupos A, B, C) são
calculadas por par `(curso, disciplina)`, nunca por disciplina isolada.

## RN02 — Periodicidade de oferta é um critério de recorte por modo de uso, não obrigatoriedade

O sistema tem **dois modos de uso**, confirmados com a coordenadora:

1. **Oferta extraordinária:** avaliar disciplinas cuja periodicidade
   regular diverge do semestre avaliado (ex.: Cálculo 3, normalmente só
   ímpar, sendo avaliada para o semestre par). Critério original do
   projeto — ver RN03.
2. **Demanda no semestre regular:** mesmo quando a disciplina já é
   ofertada normalmente naquele semestre, saber quantos alunos de cada
   curso demandam a disciplina — especialmente relevante quando ela é
   compartilhada por vários cursos (ex.: "5 alunos da Elétrica, 3 da
   Engenharia de Telecomunicações" para Cálculo 3). Não envolve cálculo de número
   de turmas, apenas a contagem de alunos por curso.

Em nenhum dos dois modos o critério de seleção é obrigatoriedade/
optatividade da disciplina — isso nunca fez parte da regra. A diferença
entre os modos é apenas **se o filtro de periodicidade divergente é
aplicado (modo 1) ou não (modo 2)** — o cálculo de demanda (Grupos A, B, C)
é o mesmo nos dois casos.

## RN03 — Periodicidade de oferta é inferida do histórico, não vem no PPC

O PPC não tem campo de periodicidade de oferta. Regra confirmada:
**"ímpar" = 1º semestre do ano civil, "par" = 2º semestre** (ex.: 2026/01
é ímpar) — não se refere à paridade do ano civil.

Regra de inferência, aplicada por `(curso, disciplina)` a partir do
histórico de matrículas:
- Só apareceu no 1º semestre, em todos os anos observados → **ímpar**
- Só apareceu no 2º semestre, em todos os anos observados → **par**
- Apareceu em ambos → **ambos**, fora do escopo de análise (já ofertada regularmente nos dois)
- Períodos letivos especiais (verão/inverno) não entram nessa classificação

## RN04 — Mapeamento de situação do histórico para estado canônico

| Situação real (histórico) | Estado canônico |
|---|---|
| Aprovado com nota, Aprovado sem nota, Aproveitamento, Aproveitamento de Créditos, Dispensado com nota, Dispensado sem nota | **aprovado** |
| Reprovado com nota, Reprovado por Frequência, Reprovado sem nota | **reprovado** |
| Matrícula | **cursando** |
| Trancamento parcial, Trancamento Total, Trancamento por Estado de Calamidade Pública | **trancado** |
| SOD, Disciplina Não Concluída, Incompleto, Mobilidade Acadêmica | **indefinido** |

**RN04.1 (provisória):** o estado `indefinido` é tratado como **não
aprovado** para fins de verificação de pré-requisito — critério
conservador, para não superestimar demanda. Pendente de validação da
coordenadora.

## RN05 — Exclusão de alunos evadidos dos Grupos B e C

Alunos com situação de matrícula `Abandono`, `Cancelamento`,
`Desligamento`, `Falecimento` ou `Cancelamento Sisu e Guri` são excluídos
das análises dos Grupos B e C. `Aluno Regular` é sempre mantido;
`Formado`, `Transferência voluntária` e `Reopção de Curso` são avaliados
caso a caso conforme o objetivo da consulta.

## RN06 — Conceito de disciplina: código não é identidade estável

O código de uma disciplina pode mudar entre reformas curriculares (ex.:
Cálculo I aparece como `AL0001`, `AL0363` e `DAL2002` ao longo do tempo,
para o mesmo conceito). Usar o campo `equivalencias` como base de
agrupamento **não funciona**: testado nos dados reais, o agrupamento
transitivo por esse campo mistura disciplinas completamente diferentes
(Cálculo, Física e Álgebra Linear caem no mesmo grupo).

**Confirmado com dados reais de Engenharia Civil:** a `versão PPC`
registrada no histórico do aluno **não prevê de forma confiável** qual
código foi usado. Um aluno com versão PPC 2023 apareceu matriculado sob o
código antigo `AL0001` em 2023/2, enquanto outro aluno de versão PPC 2010
já aparece com o código novo `AL0363` em 2023/1 — os dois códigos
convivem no mesmo período letivo. Ou seja, não é seguro assumir "código
mais recente = código correto para o período atual".

**Regra proposta:** introduzir uma entidade de **conceito de disciplina**
(`CONCEITO_DISCIPLINA`, ver schema em `docs/04-arquitetura/system-design.md`),
construída agrupando por `(curso, nome_disciplina normalizado)` — tanto os
códigos vistos no currículo quanto os vistos no histórico. Código deixa de
ser a chave usada nas regras de negócio; o conceito passa a ser.

## RN06.1 — Definição vigente do currículo vs. verificação de histórico do aluno (proposta — pendente de confirmação)

O conceito de disciplina serve dois propósitos distintos, que não podem
ser confundidos:

1. **Definição vigente do currículo** (pré-requisitos, periodicidade,
   tipo): escolhida a partir da linha `ATIVA` mais recente entre os
   códigos do conceito. Aqui, sim, há uma única resposta "correta".
2. **Verificação do histórico de um aluno** (ele já cursou/passou nesta
   disciplina?): deve considerar **todos** os códigos históricos do
   conceito, não só o vigente. Um aluno aprovado em `AL0001` em 2009 conta
   como aprovado no conceito "Cálculo I", mesmo que hoje o código vigente
   seja `AL0363`.

**Consequência prática:** nenhum registro de histórico é descartado ou
sobrescrito durante a importação — o código bruto original é sempre
preservado. A resolução para o conceito acontece ao consultar os Grupos A,
B e C, não na hora de importar os dados.

## RN07 — Equivalências entre códigos no cumprimento de pré-requisito 
A lista de pré-requisitos de uma disciplina mistura duas lógicas: exigência
de disciplinas distintas (E) e alternativas equivalentes da mesma exigência
(OU). 
**Regra proposta:** dois códigos na mesma lista de pré-requisitos são
tratados como alternativos (OU) apenas se um aparecer no campo
`equivalencias` do outro; caso contrário, são exigências distintas (E).
Para checar se um aluno cumpriu um pré-requisito específico, aceitar
`aprovado` no código exato ou em qualquer código listado no campo
`equivalencias` **daquela linha**, sem encadear a busca de forma
transitiva (ver justificativa em RN06 sobre por que a transitividade global
não é confiável nestes dados).

## RN08 — Fórmula de demanda estimada

```
demanda_estimada(disciplina, curso) =
    Σ probabilidade_reprovacao(aluno) para aluno em Grupo A
  + |Grupo B|
  + Σ probabilidade_aprovacao(aluno)  para aluno em Grupo C
```

O Grupo A não é somado como contagem bruta porque apenas alunos que **reprovarem** gerarão nova demanda no próximo semestre. Alunos aprovados saem da disciplina. Ver RN10.

## RN09 — Estimativa de probabilidade de aprovação (Grupo C) — Nível 1 (MVP)

Para o MVP, a probabilidade de aprovação de um aluno cursando um
pré-requisito é a **taxa histórica agregada de aprovação daquela
disciplina** (mesmo valor para todos os alunos do Grupo C nessa
disciplina). Refinamentos condicionados ao histórico individual do aluno
(Nível 2) ou a notas parciais do semestre corrente (Nível 3) ficam fora do
escopo do MVP.

## RN10 — Estimativa de probabilidade de reprovação (Grupo A) — Nível 1 (MVP)

Solicitado pela coordenadora na revisão final: o Grupo A não deve ser
contado como demanda certa — alunos que já cursam a disciplina agora só
gerarão demanda futura se **reprovarem**.

Para o MVP (Nível 1), a probabilidade de reprovação de cada aluno é:

```
probabilidade_reprovacao = 1 - taxa_historica_aprovacao(disciplina)
```

Sendo a `taxa_historica_aprovacao` a mesma função já usada para o Grupo C
(`probabilidade_aprovacao_nivel1`), calculada sobre todo o histórico de
alunos que já concluíram a disciplina (aprovados + reprovados).

Estrutura análoga à do Grupo C: cada aluno do Grupo A retorna um objeto com
`matricula` e `probabilidade_reprovacao`, preparado para receber cálculo
individual (Nível 2) quando o sistema evoluir.
