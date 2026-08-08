# OKF Semantic IR PoC

This PoC treats OKF as a human-readable semantic source that can be compiled into AI-friendly representations.

The design goal is deliberately small: **OKF defines only the syntax; GPT or another model proposes the meaning.**

## Minimal grammar

Only these four forms are part of the semantic tag grammar:

```text
#[Name]
#[Name[@type:Type]]
#[Name := Definition]
#[Name [[Input]] => [[Output]]]
```

Examples:

```text
#[DFS]
#[DFS[@type:Algorithm]]
#[DFS := 深さ優先探索]
#[DFS [[Graph]] => [[TraversalResult]]]
```

The forms may appear as separate lines for the same concept. The compiler aggregates them into one semantic concept.

## Division of responsibility

### OKF side

OKF only records confirmed semantic structure:

- concept name
- selected type
- selected definition
- selected input/output signature

It does **not** try to infer meaning by itself.

### GPT / AI side

An AI may read ordinary prose and propose candidates such as:

```text
Candidate type:
1. Algorithm
2. SearchMethod
3. GraphTraversal
```

or:

```text
Candidate definition:
1. 深さ優先探索
2. グラフを深さ方向に探索するアルゴリズム
```

The human selects or edits the candidate, and only the selected result is written back as OKF.

That keeps the file deterministic while allowing the intelligence layer to be replaced later.

## Concept model

These lines:

```text
#[DFS]
#[DFS[@type:Algorithm]]
#[DFS := 深さ優先探索]
#[DFS [[Graph]] => [[TraversalResult]]]
```

compile conceptually to:

```text
Concept: DFS
├─ type: Algorithm
├─ definition: 深さ優先探索
├─ input: Graph
└─ output: TraversalResult
```

## AI workflow

The intended authoring flow is:

```text
ordinary human text
      ↓
GPT reads context
      ↓
GPT proposes OKF candidates
      ↓
human selects / edits
      ↓
minimal OKF tags
      ↓
compiler
      ├─ AST JSON
      ├─ graph JSON
      ├─ JSONL
      └─ compact LLM context
```

In other words, humans should not need to manually design an AST. The AI assists with semantic annotation, while OKF remains the stable interchange format.

## Compiler

```bash
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format ast
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format graph
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format jsonl
python okf/semantic_ir/okf_ir.py okf/semantic_ir/examples/thought.okf --format prompt
```

Normal Markdown lines are ignored by the semantic compiler. Only lines beginning with `#[` are interpreted.

## Why keep it this small?

A larger grammar would encode model-specific assumptions into the knowledge format. This version instead makes the boundary explicit:

```text
AI = inference and candidate generation
OKF = accepted semantic facts
Git = history and review
```

That lets GPT, Claude, Gemini, a local model, or a future model all work against the same source without rewriting the stored knowledge.
