#!/usr/bin/env python3
"""Connect an external OKF checkout to this repository's root Obsidian vault."""
import argparse
import os
from pathlib import Path


def connect(okf_root, vault_root, check=False):
    okf_root = Path(okf_root).expanduser().resolve(strict=True)
    vault_root = Path(vault_root).expanduser().resolve(strict=True)
    if okf_root == vault_root or vault_root in okf_root.parents or okf_root in vault_root.parents:
        raise ValueError("Keep OKF and KQI in separate, non-nested directories.")
    if not (okf_root / "src" / "reference_agent").is_dir():
        raise ValueError("Expected the OKF directory containing src/reference_agent.")
    if not (vault_root / ".obsidian").is_dir():
        raise ValueError("The KQI root must contain .obsidian.")
    parent = okf_root / "vault"
    if parent.is_symlink():
        raise ValueError("Refusing to use a symlink as OKF's vault directory.")
    link = parent / "KQI"
    if os.path.lexists(link):
        if link.is_symlink() and link.resolve() == vault_root:
            return "Connected: " + str(link) + " -> " + str(vault_root)
        raise FileExistsError("Existing path preserved: " + str(link) +
                              ". Back up and reconcile its notes before moving it aside.")
    if check:
        raise FileNotFoundError("Not connected: " + str(link))
    parent.mkdir(exist_ok=True)
    link.symlink_to(vault_root, target_is_directory=True)
    return "Connected: " + str(link) + " -> " + str(vault_root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--okf", required=True, help="External OKF directory")
    parser.add_argument("--check", action="store_true", help="Check without changing files")
    args = parser.parse_args()
    try:
        print(connect(args.okf, Path(__file__).resolve().parents[1], args.check))
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
