# OfertaPampa - Sistema de Apoio à Decisão de Oferta de Disciplinas — UNIPAMPA

Sistema de apoio à decisão para a coordenação acadêmica avaliar a demanda
por disciplinas em dois cenários: (1) oferta extraordinária, fora do
semestre em que a disciplina normalmente é ofertada; e (2) demanda no
semestre regular, útil sobretudo quando a disciplina é compartilhada por
vários cursos, com base em PPCs e históricos escolares dos alunos.

## Sobre o projeto

Bolsa de Gestão Acadêmica — UNIPAMPA. O sistema não substitui o sistema
acadêmico da universidade: ele consome exportações dele (PPCs e históricos
em CSV) para estimar, para uma disciplina, três grupos de alunos:

- **Matriculados** atualmente na disciplina.
- **Aptos, não matriculados** — já cumpriram todos os pré-requisitos.
- **Potenciais** — cursando algum pré-requisito agora, com probabilidade
  estimada de aprovação e, portanto, de matrícula futura.

A soma desses grupos gera a demanda estimada — exibida por curso quando a
disciplina é compartilhada (ex.: "5 alunos da Elétrica, 3 da Engenharia de
Software") — que orienta a decisão da coordenação. O sistema **não**
calcula número de turmas a abrir; entrega apenas a contagem de alunos.

## Documentação

A documentação completa do projeto está organizada em dois lugares:

- **[Wiki do repositório](../../wiki)** — requisitos funcionais e não
  funcionais, regras de negócio, entrevista com a coordenadora, personas e
  storyboard. Ponto de partida recomendado para quem está entrando no
  projeto agora.
- **[`docs/`](./docs)** — documentação técnica versionada junto com o
  código: system design, contratos de dados, schema do banco e decisões de
  arquitetura (ADRs). 

## Status do projeto

🚧 Em fase de especificação — modelagem de dados e contratos definidos a
partir dos CSVs reais de currículo e histórico escolar. Desenvolvimento
ainda não iniciado.

## Estrutura do repositório

```
├── docs/              # Documentação técnica (ver docs/README.md)
├── etl/               # Scripts de importação dos CSVs (a criar)
├── src/                # Motor de regras: Grupos A/B/C, probabilidade (a criar)
├── data/
│   ├── raw/           # Dados reais — NUNCA versionado (.gitignore)
│   └── sample/        # Dados fictícios para desenvolvimento/testes
└── README.md
```

## Dados sensíveis

Os históricos escolares contêm dados pessoais de alunos (LGPD). **Nunca
commitar dados reais no repositório**, mesmo privado. Ver `.gitignore` e
usar `data/sample/` com dados fictícios para qualquer exemplo versionado.

## Equipe

- Bolsistas de gestão responsáveis pelo projeto: [Tauani Sauceda e Izabel Boaventura]
- Coordenação acadêmica: [Natalia Braun Chagas]
