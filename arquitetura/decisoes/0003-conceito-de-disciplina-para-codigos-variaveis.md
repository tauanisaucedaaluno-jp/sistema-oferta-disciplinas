# ADR 0003 — Conceito de disciplina para códigos que mudam ao longo do tempo

**Status:** Proposto — pendente de validação com mais cursos
**Data:** 12/08/2026
**Relacionado a:** RN06, RN06.1, RN07 (`docs/02-regras-de-negocio/regras-de-negocio.md`)

## Contexto

O código de uma disciplina não é estável ao longo de reformas curriculares.
Exemplo real confirmado em dois cursos diferentes:

- **Ciência da Computação:** Cálculo I aparece como `AL0001`, `AL0363` e
  `DAL2002`, todos representando o mesmo conteúdo em versões diferentes do
  PPC.
- **Engenharia Civil:** o mesmo padrão se repete (`AL0001` → `AL0363`), com
  um agravante — **a `versão PPC` registrada no histórico do aluno não
  prevê de forma confiável qual código foi usado.** Um aluno com versão
  PPC 2023 apareceu matriculado sob o código antigo `AL0001` em 2023/2,
  enquanto outro aluno de versão PPC 2010 já aparece com o código novo
  `AL0363` em 2023/1 — os dois códigos convivem no mesmo período letivo.

Uma primeira tentativa de solução usou o campo `equivalencias` do
currículo, unindo transitivamente todos os códigos citados juntos em
qualquer linha. Essa abordagem **falhou nos dados reais**: o agrupamento
transitivo conectou, em poucos saltos, disciplinas completamente
diferentes (Cálculo, Física, Álgebra Linear) num único grupo de ~70
códigos, porque o campo `equivalencias` nem sempre representa uma relação
de equivalência verdadeira e simétrica — em alguns casos, reflete uma
substituição curricular pontual entre disciplinas que não são, de fato, o
mesmo conceito.

Adicionalmente, descobriu-se que a coluna `versao` (não `situacao`, que é
quase sempre `ATIVA` e por isso pouco informativa) marca cada versão do
PPC como `ATIVO`, `CORRENTE` ou `INATIVO` — e **mais de uma versão pode
estar `ATIVO` simultaneamente** para o mesmo curso e disciplina, cada uma
potencialmente com pré-requisitos diferentes (confirmado nos dados: 185
pares curso/disciplina têm mais de uma versão `ATIVO` ao mesmo tempo).
Isso significa que não existe uma única "definição vigente" válida para
todos os alunos ao mesmo tempo — apenas uma definição `CORRENTE`, que é a
aplicável a alunos que ingressam agora.

## Decisão

1. **Introduzir a entidade `CONCEITO_DISCIPLINA`**, escopada por curso,
   representando a identidade estável de uma disciplina ao longo de
   reformas curriculares — independente do código usado em cada versão.

2. **Construir o mapeamento código → conceito combinando dois critérios**,
   sem encadear transitivamente:
   - Nome de disciplina normalizado igual, dentro do mesmo curso (cobre a
     maioria dos casos, ex.: `AL0001`/`AL0363`, ambos "CALCULO I").
   - Vínculo direto e local no campo `equivalencias` de uma linha
     específica, sem seguir a cadeia além de um salto (cobre casos de
     renomeação, ex.: `DAL2002` "CALCULO A" → `AL0001` "CALCULO I").

3. **Separar dois usos do conceito, que não podem ser confundidos**
   (RN06.1):
   - *Definição vigente do currículo* (pré-requisitos, periodicidade,
     tipo): usa a linha marcada `versao = CORRENTE` como referência
     padrão para o MVP — uma simplificação assumida conscientemente (ver
     limitação abaixo).
   - *Verificação de histórico do aluno*: considera **todos** os códigos
     históricos do conceito, nunca só o vigente. Nenhum registro de
     histórico é descartado ou reescrito na importação — a resolução para
     conceito acontece em tempo de consulta.

## Consequências

**Positivas:**
- Um aluno aprovado sob um código antigo é corretamente reconhecido como
  tendo cumprido o pré-requisito, independentemente de qual código está
  vigente hoje.
- O modelo não depende de o campo `equivalencias` ser globalmente
  consistente — usa só vínculos diretos, evitando a explosão observada na
  tentativa transitiva.

**Negativas / custos e limitações conhecidas:**
- **Simplificação assumida para o MVP:** usar sempre a versão `CORRENTE`
  como definição de pré-requisitos ignora que alunos vinculados a uma
  versão `ATIVO` mais antiga podem estar sujeitos a pré-requisitos
  diferentes. Isso pode gerar Grupos B/C levemente incorretos para esses
  alunos. Uma versão futura mais precisa resolveria os pré-requisitos por
  aluno, cruzando a `versão PPC` do histórico com o `num_versao`
  correspondente no currículo — não implementado no MVP por complexidade.
- **Casos não cobertos:** disciplinas que mudam de nome **e** não têm
  vínculo direto no campo `equivalencias` de nenhuma linha permanecem
  invisíveis ao agrupamento — ficam como códigos "órfãos", reportados
  como exceção pelo ETL (RF05), não resolvidos automaticamente.
- Validado até agora em apenas dois cursos (Ciência da Computação e
  Engenharia Civil) — a regra de agrupamento por nome pode precisar de
  ajuste ao testar outros cursos.

## Alternativas consideradas

- **Usar `equivalencias` de forma transitiva (união de componentes
  conexos):** testada e descartada — mistura disciplinas não relacionadas
  (ver evidência acima).
- **Usar apenas a `versão PPC` do aluno para prever o código usado:**
  testada e descartada — dados reais mostram que essa previsão não é
  confiável (código antigo aparece sob versão de PPC nova, e vice-versa).
- **Resolver pré-requisitos por aluno (usando a versão de PPC específica
  dele) desde o MVP:** mais correta, mas adiada por complexidade — ver
  limitação acima.
