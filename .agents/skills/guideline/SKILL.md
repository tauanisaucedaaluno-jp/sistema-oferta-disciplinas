---
name: guideline
description: >
  Use this skill when you need to verify that code, commits, or documentation
  follow the conventions of the Grupo 12 Estruturas de Dados project.
  Trigger when the user asks to review code quality, check conventions, or
  ensure a change is consistent with project standards.
---

# Guideline — Grupo 12 · Estruturas de Dados

Convenções do projeto para implementação, commits e documentação.

---

## Documentação canônica

| Pergunta | Onde olhar |
|----------|------------|
| Parâmetros do Grupo 12? | [README.md](../../../README.md) — seção Identificação |
| Como funciona o workload? | [scripts/gen_workload.py](../../scripts/gen_workload.py) (somente leitura) |
| Quais arquivos posso editar? | [AGENTS.md](../../../AGENTS.md) — tabela de permissões |
| Como rodar os experimentos? | [README.md](../../../README.md) — seção Como reproduzir |
| O que entregar? | [docs/](../../docs/) — PDF da especificação |

---

## Estrutura do projeto

```
grupo12/
├── src/          # Código da estrutura de dados (editável)
├── scripts/      # gen_workload.py (NÃO EDITAR) + plot_results.py
├── tests/        # Testes unitários (adicionar, nunca remover)
├── data/         # Gerado localmente — NÃO commitar
├── results/      # CSVs e .out — escrita permitida
├── report/       # Relatório e justificativa — NÃO editar (autoria do grupo)
├── prompts/      # dump_chats.md — NÃO editar (autoria do grupo)
└── docs/         # PDF da especificação — somente leitura
```

---

## Convenções de código

### Python
- Versão mínima: **Python 3.10+**
- Estilo: **snake_case** para variáveis, funções e métodos
- Type hints obrigatórios em todas as assinaturas públicas:
  ```python
  def insert(self, key: int) -> None: ...
  def rank(self, key: int) -> int: ...
  def select(self, i: int) -> int | None: ...
  def range_agg(self, a: int, b: int) -> int: ...
  ```
- Docstrings obrigatórias em métodos públicos e privados que fazem rotação
- `__slots__` nos nós para eficiência de memória

### Complexidade (regra hard)
- `rank`, `select`, `range_agg` **devem ser O(log n)** usando os campos aumentados
- Qualquer implementação que varra a árvore (O(n)) deve ser rejeitada

### Campos aumentados dos nós
- `node.height` — altura da subárvore
- `node.size` — número de nós na subárvore
- **Para o Grupo 12:** `count = size` (contagem). Não criar atributo `count` separado.
- `_update(node)` deve ser chamado após **todo** rearranjo de ponteiros

---

## Regras de rotação (crítico)

```python
# CORRETO — atualizar o filho antes da nova raiz
def _rotate_right(self, y):
    x = y.left
    T2 = x.right
    x.right = y
    y.left = T2
    self._update(y)   # y primeiro (agora é filho)
    self._update(x)   # x depois (nova raiz)
    return x

# ERRADO — não inverter a ordem de _update()
```

---

## Testes

- Arquivo: `grupo12/tests/test_avl.py`
- Framework: `unittest` (padrão) ou `pytest`
- Rodar: `python -m pytest grupo12/tests/ -v`
- **Nunca remover** testes existentes
- Adicionar testes para cada nova operação implementada
- Casos obrigatórios:
  - Inserção sorted (caso patológico)
  - `check_invariants()` após rotações
  - `rank(k)` = número exato de chaves < k
  - `select(i)` = i-ésima menor chave (0-indexado)
  - `range_agg(a, b)` = contagem exata de chaves em [a, b]

---

## Commits

Use mensagens descritivas em português ou inglês:

```
feat(avl): adiciona check_invariants() pós-rotação
fix(avl): corrige ordem de _update em rotate_left
test(avl): adiciona testes de rank e select
bench: adiciona benchmark de escala com 4 ordens de grandeza
docs: atualiza README com informações de ambiente
```

---

## Arquivos proibidos de modificar

| Arquivo | Motivo |
|---|---|
| `scripts/gen_workload.py` | Árbitro do projeto — qualquer mudança invalida o gabarito |
| `report/report.md` | Medições reais do grupo — autoria humana |
| `report/justification.md` | Argumentos do grupo — autoria humana |
| `prompts/dump_chats.md` | Dump dos chats — autoria humana (20% da nota) |

---

## Antes de qualquer PR ou entrega

```bash
# 1. Testes unitários
python -m pytest grupo12/tests/ -v

# 2. Smoke test de corretude
python grupo12/scripts/gen_workload.py generate \
  --synthetic 10000 --out grupo12/data/smoke \
  --ops 5000 --mix 40:25:35 --seed 12
python grupo12/src/main.py \
  --trace grupo12/data/smoke.trace --out grupo12/results/smoke.out
python grupo12/scripts/gen_workload.py verify \
  --expected grupo12/data/smoke.expected \
  --candidate grupo12/results/smoke.out
```

Ambos devem passar sem erros.
