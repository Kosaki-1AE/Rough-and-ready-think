#!/usr/bin/env python3
"""Remove only byte-identical copies under okf/vault/KQI; default is a dry run."""
import argparse
from pathlib import Path


def clean(root, apply=False):
    root = Path(root).resolve()
    nested = root / "okf" / "vault" / "KQI"
    if any(p.is_symlink() for p in (root / "okf", root / "okf/vault", nested)):
        raise ValueError("Refusing symlink-based paths.")
    if not nested.is_dir():
        print("No nested vault found.")
        return 0
    matched = 0
    for source in sorted(nested.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        rel = source.relative_to(nested)
        if any(part.startswith(".") for part in rel.parts):
            continue
        target = root / rel
        if any(p.is_symlink() for p in (target, *target.parents)):
            continue
        if target.is_file() and source.read_bytes() == target.read_bytes():
            matched += 1
            print(("REMOVE " if apply else "MATCH ") + str(source.relative_to(root)))
            if apply:
                source.unlink()
        else:
            print("KEEP (different or only copy) " + str(source.relative_to(root)))
    if apply:
        for directory in sorted(nested.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if directory.is_dir() and not directory.is_symlink():
                try:
                    directory.rmdir()
                except OSError:
                    pass
        for directory in (nested, nested.parent, nested.parent.parent):
            try:
                directory.rmdir()
            except OSError:
                pass
    print(str(matched) + (" duplicate files removed." if apply else " identical copies found; rerun with --apply to remove."))
    return matched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        clean(args.vault, args.apply)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
