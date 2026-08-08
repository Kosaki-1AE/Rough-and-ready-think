from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

BRANCH_RE = re.compile(
    r"^(?P<source>.+?)\s*->\s*\?\s*(?P<condition>.+?)\s*:\s*(?P<true>.+?)\s*\|\s*(?P<false>.+?)\s*$"
)


def _split_merge(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\s+\+\s+", text) if p.strip()]


def _split_fork(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\s+(?:×|\*)\s+", text) if p.strip()]


def parse_statement(raw: str, line_no: int) -> dict[str, Any] | None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    m = BRANCH_RE.match(line)
    if m:
        return {
            "type": "Branch",
            "source": m.group("source").strip(),
            "condition": m.group("condition").strip(),
            "true": m.group("true").strip(),
            "false": m.group("false").strip(),
            "line": line_no,
            "raw": raw.rstrip(),
        }

    if "->" in line:
        left, right = [x.strip() for x in line.split("->", 1)]
        inputs = _split_merge(left)
        outputs = _split_fork(right)
        if len(inputs) > 1 and len(outputs) == 1:
            return {"type": "Merge", "inputs": inputs, "output": outputs[0], "line": line_no, "raw": raw.rstrip()}
        if len(inputs) == 1 and len(outputs) > 1:
            return {"type": "Fork", "source": inputs[0], "outputs": outputs, "line": line_no, "raw": raw.rstrip()}
        if len(inputs) == 1 and len(outputs) == 1:
            return {"type": "Transition", "from": inputs[0], "to": outputs[0], "line": line_no, "raw": raw.rstrip()}
        raise ValueError(f"line {line_no}: ambiguous merge+fork expression: {line}")

    if ":" in line:
        target, value = [x.strip() for x in line.split(":", 1)]
        return {"type": "Definition", "target": target, "value": value, "line": line_no, "raw": raw.rstrip()}

    raise ValueError(f"line {line_no}: unsupported OKF semantic statement: {line}")


def parse(text: str) -> dict[str, Any]:
    statements: list[dict[str, Any]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        node = parse_statement(raw, line_no)
        if node is not None:
            node["id"] = f"n{len(statements) + 1:03d}"
            statements.append(node)
    return {"okf_ir_version": "0.1-poc", "statements": statements}


def to_graph(ast: dict[str, Any]) -> dict[str, Any]:
    nodes: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []

    def add_node(name: str) -> None:
        nodes.setdefault(name, {"id": name, "label": name})

    for stmt in ast["statements"]:
        t = stmt["type"]
        if t == "Definition":
            add_node(stmt["target"])
            nodes[stmt["target"]]["definition"] = stmt["value"]
        elif t == "Transition":
            add_node(stmt["from"]); add_node(stmt["to"])
            edges.append({"from": stmt["from"], "to": stmt["to"], "type": "transition"})
        elif t == "Merge":
            add_node(stmt["output"])
            for src in stmt["inputs"]:
                add_node(src)
                edges.append({"from": src, "to": stmt["output"], "type": "merge"})
        elif t == "Fork":
            add_node(stmt["source"])
            for dst in stmt["outputs"]:
                add_node(dst)
                edges.append({"from": stmt["source"], "to": dst, "type": "fork"})
        elif t == "Branch":
            add_node(stmt["source"]); add_node(stmt["true"]); add_node(stmt["false"])
            edges.append({"from": stmt["source"], "to": stmt["true"], "type": "branch_true", "condition": stmt["condition"]})
            edges.append({"from": stmt["source"], "to": stmt["false"], "type": "branch_false", "condition": stmt["condition"]})

    return {"okf_ir_version": ast["okf_ir_version"], "nodes": list(nodes.values()), "edges": edges}


def to_prompt(ast: dict[str, Any]) -> str:
    out = ["OKF semantic IR (v0.1-poc). Treat this as source-of-truth structure.", "Statements:"]
    for s in ast["statements"]:
        t = s["type"]
        if t == "Definition":
            desc = f'{s["target"]} := {s["value"]}'
        elif t == "Transition":
            desc = f'{s["from"]} -> {s["to"]}'
        elif t == "Merge":
            desc = f'{", ".join(s["inputs"])} -> {s["output"]}'
        elif t == "Fork":
            desc = f'{s["source"]} -> {", ".join(s["outputs"])}'
        else:
            desc = f'from {s["source"]}; if {s["condition"]} then {s["true"]} else {s["false"]}'
        out.append(f'- {s["id"]} {t}: {desc}')
    return "\n".join(out) + "\n"


def render(ast: dict[str, Any], fmt: str) -> str:
    if fmt == "ast":
        return json.dumps(ast, ensure_ascii=False, indent=2) + "\n"
    if fmt == "graph":
        return json.dumps(to_graph(ast), ensure_ascii=False, indent=2) + "\n"
    if fmt == "jsonl":
        return "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in ast["statements"])
    if fmt == "prompt":
        return to_prompt(ast)
    raise ValueError(fmt)


def main() -> None:
    ap = argparse.ArgumentParser(description="Compile semantic OKF text into AI-friendly intermediate representations.")
    ap.add_argument("input", type=Path)
    ap.add_argument("--format", choices=["ast", "graph", "jsonl", "prompt"], default="ast")
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
