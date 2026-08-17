# Requisitos Funcionais

## Importação de dados

**RF01.** O sistema deve importar dados de currículo/matriz curricular a
partir de arquivo CSV exportado do sistema acadêmico.

**RF02.** O sistema deve importar dados de histórico escolar a partir de
arquivo CSV exportado do sistema acadêmico, um arquivo por curso.

**RF03.** O sistema deve normalizar a coluna de situação do histórico para
um conjunto fixo de estados canônicos (ver Regras de Negócio, RN04).

**RF04.** O sistema deve agrupar códigos de disciplina que representam o
mesmo conceito ao longo de versões do PPC, mantendo **uma única definição
vigente de currículo** (pré-requisitos, periodicidade, tipo) por
(curso, conceito de disciplina) (ver RN06).

**RF04.1.** Ao verificar se um aluno já cursou ou está cursando uma
disciplina (Grupos A, B, C), o sistema deve considerar **todos os códigos
históricos** associados ao conceito de disciplina daquele curso — não
apenas o código vigente no currículo atual (ver RN06.1). Nenhum registro
de histórico deve ser descartado ou reescrito por esse processo; a
resolução por conceito ocorre na consulta, não na importação.

**RF05.** O sistema deve gerar um relatório de exceções/inconsistências
encontradas durante a importação (ex.: pré-requisito referenciando
disciplina inexistente, casos ambíguos de agrupamento por conceito, código
de histórico sem conceito correspondente conhecido), para revisão manual —
não deve falhar silenciosamente.

## Análise de demanda

**RF06.** O sistema deve permitir dois modos de análise de demanda (ver
RN02 em Regras de Negócio): (a) **oferta extraordinária** — restrita a
disciplinas cuja periodicidade regular diverge do semestre avaliado; (b)
**demanda no semestre regular** — para qualquer disciplina no semestre em
que ela já é normalmente ofertada, sem esse filtro, exibindo a demanda
desagregada por curso (ex.: "5 alunos da Elétrica, 3 da Engenharia de
Software").

**RF06.1.** No modo "oferta extraordinária", o sistema deve identificar
automaticamente quais disciplinas são candidatas (aquelas cuja
periodicidade diverge do semestre avaliado).

**RF07.** Para cada disciplina candidata e curso, o sistema deve calcular
o **Grupo A** (alunos matriculados na disciplina no período atual).

**RF08.** Para cada disciplina candidata e curso, o sistema deve calcular
o **Grupo B** (alunos aptos — cumpriram todos os pré-requisitos — e não
matriculados na disciplina).

**RF09.** Para cada disciplina candidata e curso, o sistema deve calcular
o **Grupo C** (alunos cursando algum pré-requisito no período atual, com
probabilidade estimada de aprovação).

**RF10.** O sistema deve estimar a probabilidade de aprovação de um aluno
do Grupo C usando, no mínimo, a taxa histórica de aprovação da disciplina
(Nível 1, ver ADR correspondente em `docs/`).

**RF11.** O sistema deve calcular a demanda total estimada por
(disciplina, curso) como a soma do Grupo A, Grupo B e a soma das
probabilidades de aprovação do Grupo C.

**RF12.** O sistema deve consolidar a demanda por disciplina quando ela for
compartilhada entre múltiplos cursos, exibindo também a quebra por curso.
Aplica-se aos dois modos de análise definidos em RF06.

## Painel de gestão (dashboard)

**RF13.** O sistema deve exigir autenticação (login e senha) para acesso
ao painel de gestão.

**RF14.** O sistema deve permitir ao usuário escolher o modo de análise
(oferta extraordinária ou demanda no semestre regular — ver RF06) ao
consultar uma disciplina.

**RF15.** O sistema deve exibir, para cada disciplina candidata, os
valores dos Grupos A, B, C e a demanda total estimada, desagregada por
curso quando a disciplina for compartilhada (ver RF12).

**RF16.** O sistema deve permitir filtrar a visualização por curso e por
disciplina.

**RF17.** O sistema deve permitir exportar os dados exibidos no painel
(CSV/planilha).
