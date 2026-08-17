---
name: improve-codebase-architecture
description: >
  Encontra oportunidades de melhoria na arquitetura do projeto de AVL do Grupo 12.
  Use quando o usuário quiser refatorar código, melhorar a testabilidade, identificar
  módulos rasos ou verificar se a estrutura de dados respeita as complexidades exigidas.
---

# Melhoria de Arquitetura — Grupo 12 · AVL Aumentada

Identifica fricções arquiteturais no projeto de Estruturas de Dados e propõe
**oportunidades de aprofundamento** — refatorações que tornam módulos rasos em profundos,
melhorando testabilidade e navegabilidade.

> ⚠️ **Escopo restrito:** Este skill aplica-se apenas ao código Python dentro de
> `grupo12/src/`. Nunca modificar `scripts/gen_workload.py`.

---

## Glossário (usar exatamente esses termos)

- **Módulo** — qualquer coisa com interface e implementação (`AVLTree`, `_rotate_right`, `benchmark`).
- **Interface** — o que o chamador precisa saber: assinaturas, tipos, invariantes, casos de erro.
- **Profundidade** — muito comportamento atrás de uma interface pequena. **Profundo** = alto leverage. **Raso** = interface quase tão complexa quanto a implementação.
- **Costura** (*seam*) — onde uma interface vive; lugar onde comportamento pode ser alterado sem edição interna.
- **Locality** — bugs, mudanças e conhecimento concentrados em um lugar.

---

## Áreas críticas do projeto para inspecionar

### 1. `avl_tree.py` — núcleo da estrutura

Perguntas a fazer durante a exploração:

| Pergunta | Sinal de problema |
|---|---|
| `_update(node)` é chamado na ordem correta em **todas** as rotações? | `size` incorreto → `rank`/`select`/`range_agg` silenciosamente errados |
| `rank`, `select` e `range_agg` usam `size` sem varrer a árvore? | Qualquer loop que percorra nós = O(n) = bug de complexidade |
| `check_invariants()` existe e verifica `height` e `size` recursivamente? | Ausente = bugs de rotação invisíveis |
| Rotações duplas chamam `_update` nos **dois** passos, na ordem correta? | Só no passo final = dados corrompidos silenciosamente |

**Teste de deleção:** Se `_update(node)` fosse deletado, todos os chamadores precisariam recalcular `height` e `size` manualmente — sinal de que ele é um módulo profundo merecedor de seu lugar.

### 2. `main.py` — orquestrador do trace

- Não deve conter lógica de árvore — só lê o `.trace` e delega para `AVLTree`.
- Se houver condicional `if op == 'I':` com lógica interna → candidato a mover para `AVLTree`.

### 3. `benchmark.py` — medições empíricas

- Isolamento de tempo: usa `time.perf_counter()` ao redor de blocos de operações?
- Percentis: usa `numpy.percentile` sobre amostras individuais?
- Não deve misturar lógica de árvore com lógica de medição.

### 4. `naive_bst.py` — linha de base

- Interface idêntica à `AVLTree`? (`insert`, `delete`, `search`, `rank`, `select`, `range_agg`)
- Se não for drop-in replacement, o benchmark não é comparável.

---

## Processo

### 1. Explorar

Percorra organicamente o código em `grupo12/src/`. Anote onde há fricção:

- Onde entender um conceito exige navegar por muitos arquivos pequenos?
- Onde módulos são **rasos** — interface quase tão complexa quanto a implementação?
- Onde a complexidade O(log n) pode estar sendo violada silenciosamente?
- Quais partes são difíceis de testar pela interface pública atual?

### 2. Apresentar candidatos

Para cada candidato, apresente um cartão com:

- **Arquivos** — quais módulos estão envolvidos
- **Problema** — por que está causando fricção
- **Solução** — o que mudaria em linguagem simples
- **Benefício** — em termos de locality e complexidade correta
- **Força da recomendação** — `Forte`, `Vale explorar` ou `Especulativo`

Termine com uma **Recomendação principal**: qual candidato atacar primeiro e por quê.

**Não proponha interfaces ainda.** Após apresentar, pergunte: "Qual desses você quer explorar?"

### 3. Loop de refinamento

Quando o usuário escolher um candidato, inicie uma conversa de refinamento:
- Quais invariantes o módulo refatorado deve preservar?
- Quais testes existentes sobrevivem à mudança?
- A mudança melhora ou piora a legibilidade do relatório empírico?

---

## Regras hard durante refatoração

1. Rodar `python -m pytest grupo12/tests/ -v` após qualquer mudança em `avl_tree.py`.
2. Rodar `check_invariants()` após 10.000 inserções sorted para confirmar invariantes.
3. Nunca modificar `scripts/gen_workload.py`.
4. Nunca introduzir estrutura auxiliar que mude a complexidade assintótica.
