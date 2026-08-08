# OKF Semantic IR PoC

This directory is a small, runnable proof of concept for treating OKF as a **human-authored knowledge source that can be compiled into AI-friendly intermediate representations**.

The existing OKF in this repository remains untouched. This layer only adds a semantic compiler experiment on top of it.

## Idea

```text
human thought
    ↓
*.okf semantic text
    ↓
parser / compiler
    ├─ AST JSON
    ├─ graph JSON
    ├─ JSONL
    └─ compact LLM prompt context
```

The important part is that the source stays vendor-neutral. GPT, Claude, Gemini, a local model, a graph database, or a future system can consume a representation generated from the same source.

## Minimal syntax

```text
A : definition
A -> B
A + B -> C
A -> B × C
A -> ? condition : B | C
```

Meaning:

| Syntax | AST node | Meaning |
|---|---|---|
| `A : x` | `Definition` | define A as x |
| `A -> B` | `Transition` | A transitions to B |
| `A + B -> C` | `Merge` | multiple inputs converge on C |
| `A -> B × C` | `Fork` | one source produces multiple outputs |
| `A -> ? cond : B \| C` | `Branch` | conditional transition |

`*` can be used instead of `×` when typing on an ASCII-only keyboard.

This is intentionally a PoC grammar, not a final specification.

## Try it

From the repository root:

```bash
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format ast
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format graph
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format jsonl
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format prompt
```

Write to a file with `-o`:

```bash
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf \
  --format ast \
  -o /tmp/thought.ast.json
```

## Why this matters

A normal second-brain workflow stores notes and relies on a human or AI to reconstruct structure later. This experiment instead stores enough **semantic relations** that the structure can be compiled deterministically.

Git then gives the semantic source a timeline for free:

- commits = changes in thought
- diffs = changes in meaning
- branches = competing hypotheses
- merges = accepted integration

The AI becomes a replaceable reader/transformer rather than the owner of the knowledge.
