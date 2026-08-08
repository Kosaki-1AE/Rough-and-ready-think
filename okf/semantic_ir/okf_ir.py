from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

TYPE_RE = re.compile(r"^#\[(?P<name>.+?)\[@type:(?P<semantic_type>[^\]]+)\]\]$")
DEF_RE = re.compile(r"^#\[(?P<name>.+?)\s*:=\s*(?P<definition>.+?)\]$")
SIG_RE = re.compile(
    r"^#\[(?P<name>.+?)\s+"
    r"(?P<inputs>(?:\[\[[^\]]+\]\](?:\s*,?\s*)*)+)\s*=>\s*"
    r"(?P<outputs>(?:\[\[[^\]]+\]\](?:\s*,?\s*)*)+)\]$"
)
BASE_RE = re.compile(r"^#\[(?P<name>[^\[\]]+)\]$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _clean(value: str) -> str:
    return value.strip()


def _links(value: str) -> list[str]:
    return [_clean(x) for x in WIKILINK_RE.findall(value)]


def parse_statement(raw: str, line_no: int) -> dict[str, Any] | None:
    line = raw.strip()

    # The semantic tags are intentionally embeddable in normal Markdown.
    # Only lines beginning with "#[" are interpreted by this compiler.
    if not line or not line.startswith("#["):
        return None

    m = TYPE_RE.match(line)
    if m:
        return {
            "kind": "Type",
            "name": _clean(m.group("name")),
            "semantic_type": _clean(m.group("semantic_type")),
            "line": line_no,
            "raw": raw.rstrip(),
        }

    m = DEF_RE.match(line)
    if m:
        return {
            "kind": "Definition",
            "name": _clean(m.group("name")),
            "definition": _clean(m.group("definition")),
            "line": line_no,
            "raw": raw.rstrip(),
        }

    m = SIG_RE.match(line)
    if m:
        inputs = _links(m.group("inputs"))
        outputs = _links(m.group("outputs"))
        if not inputs or not outputs:
            raise ValueError(
                f"line {line_no}: signature requires at least one input and output"
            )
        return {
            "kind": "Signature",
            "name": _clean(m.group("name")),
            "inputs": inputs,
            "outputs": outputs,
            "line": line_no,
            "raw": raw.rstrip(),
        }

    m = BASE_RE.match(line)
    if m:
        return {
            "kind": "Concept",
            "name": _clean(m.group("name")),
            "line": line_no,
            "raw": raw.rstrip(),
        }

    raise ValueError(
        f"line {line_no}: unsupported OKF tag. "
        "Allowed forms are #[Name], #[Name[@type:Type]], "
        "#[Name := Definition], #[Name [[Input]] => [[Output]]]"
    )


def aggregate_concepts(statements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    concepts: dict[str, dict[str, Any]] = {}

    def concept(name: str) -> dict[str, Any]:
        return concepts.setdefault(
            name,
            {
                "name": name,
                "types": [],
                "definitions": [],
                "inputs": [],
                "outputs": [],
            },
        )

    for stmt in statements:
        c = concept(stmt["name"])
        kind = stmt["kind"]

        if kind == "Type" and stmt["semantic_type"] not in c["types"]:
            c["types"].append(stmt["semantic_type"])
        elif kind == "Definition" and stmt["definition"] not in c["definitions"]:
            c["definitions"].append(stmt["definition"])
        elif kind == "Signature":
            for item in stmt["inputs"]:
                if item not in c["inputs"]:
                    c["inputs"].append(item)
                concept(item)
            for item in stmt["outputs"]:
                if item not in c["outputs"]:
                    c["outputs"].append(item)
                concept(item)

    return list(concepts.values())


def parse(text: str) -> dict[str, Any]:
    statements: list[dict[str, Any]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        node = parse_statement(raw, line_no)
        if node is not None:
            node["id"] = f"n{len(statements) + 1:03d}"
            statements.append(node)

    return {
        "okf_semantic_version": "0.2-minimal",
        "grammar": [
            "#[Name]",
            "#[Name[@type:Type]]",
            "#[Name := Definition]",
            "#[Name [[Input]] => [[Output]]]",
        ],
        "statements": statements,
        "concepts": aggregate_concepts(statements),
    }


def to_graph(ast: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    edges: list[dict[str, str]] = []

    for c in ast["concepts"]:
        node: dict[str, Any] = {"id": c["name"], "label": c["name"]}
        if c["types"]:
            node["types"] = c["types"]
        if c["definitions"]:
            node["definitions"] = c["definitions"]
        nodes.append(node)

        for semantic_type in c["types"]:
            edges.append({"from": c["name"], "to": semantic_type, "type": "is_a"})
        for src in c["inputs"]:
            edges.append({"from": src, "to": c["name"], "type": "input"})
        for dst in c["outputs"]:
            edges.append({"from": c["name"], "to": dst, "type": "output"})

    known = {node["id"] for node in nodes}
    referenced = {edge["to"] for edge in edges} | {edge["from"] for edge in edges}
    for name in sorted(referenced - known):
        nodes.append({"id": name, "label": name})

    return {
        "okf_semantic_version": ast["okf_semantic_version"],
        "nodes": nodes,
        "edges": edges,
    }


def to_prompt(ast: dict[str, Any]) -> str:
    out = [
        "OKF semantic context.",
        "The following structure is source-of-truth. Do not invent missing types, definitions, inputs, or outputs.",
        "",
    ]

    for c in ast["concepts"]:
        parts = [f"- {c['name']}"]
        if c["types"]:
            parts.append(f"type={', '.join(c['types'])}")
        if c["definitions"]:
            parts.append(f"definition={'; '.join(c['definitions'])}")
        if c["inputs"] or c["outputs"]:
            ins = ", ".join(c["inputs"]) or "∅"
            outs = ", ".join(c["outputs"]) or "∅"
            parts.append(f"signature=({ins}) => ({outs})")
        out.append(" | ".join(parts))

    return "\n".join(out) + "\n"


def render(ast: dict[str, Any], fmt: str) -> str:
    if fmt == "ast":
        return json.dumps(ast, ensure_ascii=False, indent=2) + "\n"
    if fmt == "graph":
        return json.dumps(to_graph(ast), ensure_ascii=False, indent=2) + "\n"
    if fmt == "jsonl":
        return "".join(
            json.dumps(s, ensure_ascii=False) + "\n" for s in ast["statements"]
        )
    if fmt == "prompt":
        return to_prompt(ast)
    raise ValueError(fmt)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compile the minimal OKF tag grammar into AI-friendly representations."
    )
    ap.add_argument("input", type=Path)
    ap.add_argument(
        "--format",
        choices=["ast", "graph", "jsonl", "prompt"],
        default="ast",
    )
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()

    ast = parse(args.input.read_text(encoding="utf-8"))
    output = render(ast, args.format)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
