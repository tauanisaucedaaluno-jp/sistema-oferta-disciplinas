# Documentação técnica

Esta pasta contém a documentação que precisa **versionar junto com o
código** — muda por Pull Request, tem histórico revisável, e é a fonte de
verdade técnica do projeto.

## O que fica aqui vs. o que fica na Wiki

- **`docs/` (esta pasta):** requisitos, regras de negócio, arquitetura e
  decisões técnicas (ADRs). Qualquer mudança aqui deve acontecer no mesmo
  Pull Request que a mudança de código correspondente, sempre que possível.
- **[Wiki do repositório](../../../wiki):** entendimento do problema —
  entrevista com a coordenadora, personas, storyboard, protótipo. Conteúdo
  mais "vivo", consultado por quem não necessariamente lê código.

## Estrutura

```
docs/
├── 01-requisitos/
│   ├── requisitos-funcionais.md       ← RF01, RF02...
│   └── requisitos-nao-funcionais.md   ← RNF01, RNF02...
├── 02-regras-de-negocio/
│   └── regras-de-negocio.md           ← RN01, RN02...
└── 04-arquitetura/
    ├── system-design.md               ← visão técnica: componentes, schema, fluxo de dados
    └── decisoes/                      ← ADRs — um arquivo por decisão arquitetural
```

## Convenção de referência cruzada

Requisitos (`RF##`/`RNF##`), regras de negócio (`RN##`) e decisões
arquiteturais (ADRs numerados) devem ser referenciados pelo identificador
em qualquer lugar do projeto — issues, Pull Requests, comentários de
código. Isso permite rastrear, por exemplo, qual linha de código
implementa qual regra.

## Antes de editar

- Regras marcadas como **provisórias** no `regras-de-negocio.md` ainda não
  foram validadas pela coordenação acadêmica — não trate como definitivas.
- Ao criar uma decisão de arquitetura nova (ex.: escolha de banco de dados,
  mudança de modelo de dados), registre como ADR em `04-arquitetura/decisoes/`,
  não apenas como comentário de código ou mensagem de commit.
