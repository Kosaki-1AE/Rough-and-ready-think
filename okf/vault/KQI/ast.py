import re
from pathlib import Path

vault = Path("/Users/ユーザー名/Documents/knowledge-catalog/okf/vault/KQI")

pattern = re.compile(r"^\s*(.+?)\s*(->|:)\s*(.+?)\s*$")

relations = []

for md_file in vault.rglob("*.md"):
    for line_number, line in enumerate(
        md_file.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        match = pattern.match(line)

        if not match:
            continue

        left, operator, right = match.groups()

        relations.append(
            {
                "from": left,
                "operator": operator,
                "to": right,
                "file": str(md_file.relative_to(vault)),
                "line": line_number,
            }
        )

for relation in relations:
    print(relation)