# Sistema de Apoio à Decisão para Oferta Extraordinária de Disciplinas — UNIPAMPA

Sistema de apoio à decisão para a coordenação acadêmica avaliar a oferta de
disciplinas fora do semestre em que normalmente são ofertadas (ex.: uma
disciplina ofertada regularmente só em semestres ímpares sendo avaliada
para oferta também em um semestre par), com base em PPCs e históricos
escolares dos alunos.

## Sobre o projeto

Bolsa de Gestão Acadêmica — UNIPAMPA. O sistema não substitui o sistema
acadêmico da universidade: ele consome exportações dele (PPCs e históricos
em CSV) para estimar, para uma disciplina candidata, três grupos de alunos:

- **Matriculados** atualmente na disciplina.
- **Aptos, não matriculados** — já cumpriram todos os pré-requisitos.
- **Potenciais** — cursando algum pré-requisito agora, com probabilidade
  estimada de aprovação e, portanto, de matrícula futura.

A soma desses grupos gera a demanda estimada, que orienta a decisão da
coordenação.

## Documentação

A documentação completa do projeto está organizada em dois lugares:

- **[Wiki do repositório](../../wiki)** — requisitos funcionais e não
  funcionais, regras de negócio, entrevista com a coordenadora, personas e
  storyboard. Ponto de partida recomendado para quem está entrando no
  projeto agora.
- **[`docs/`](./docs)** — documentação técnica versionada junto com o
  código: system design e decisões de
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

- Bolsistas de gestão responsáveis pelo projeto: [Tauani Ximenes Sauceda e Izabel de Oliveira Boaventura]
- Coordenação acadêmica: [Natalia Braun Chagas]
