#!/usr/bin/env python3
"""Update the external OKF checkout, report specification changes, and connect KQI."""
import argparse
import subprocess
from pathlib import Path
from connect_okf import connect

UPSTREAM = "https://github.com/GoogleCloudPlatform/knowledge-catalog.git"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def update(target, vault):
    target = target.expanduser().absolute()
    vault = vault.resolve()
    resolved = target.resolve()
    if resolved == vault or vault in resolved.parents or resolved in vault.parents:
        raise ValueError("The upstream checkout must be outside the KQI vault.")
    if not target.exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--single-branch",
                        "--branch", "main", UPSTREAM, str(target)], check=True)
    if git(target, "rev-parse", "--show-toplevel") != str(target.resolve()):
        raise ValueError("Target must be the root of a separate Git checkout.")
    origin = git(target, "remote", "get-url", "origin").rstrip("/")
    if origin.removesuffix(".git") != UPSTREAM.removesuffix(".git"):
        raise ValueError("Unexpected origin; no update performed.")
    if git(target, "branch", "--show-current") != "main":
        raise ValueError("Expected upstream main branch.")
    if git(target, "status", "--porcelain"):
        raise ValueError("Upstream checkout has local changes; preserve/reconcile them first.")
    before = git(target, "rev-parse", "HEAD")
    spec_before = git(target, "rev-parse", "HEAD:okf/SPEC.md")
    git(target, "fetch", "origin", "main")
    # Refuse local commits, including a branch that is ahead of origin.
    if git(target, "rev-list", "origin/main..HEAD"):
        raise ValueError("Local commits exist; no automatic merge performed.")
    git(target, "merge", "--ff-only", "origin/main")
    after = git(target, "rev-parse", "HEAD")
    spec_after = git(target, "rev-parse", "HEAD:okf/SPEC.md")
    print("Upstream commit: " + after)
    if spec_before != spec_after:
        print("SPEC CHANGED: review before relying on OKF compatibility.")
        print("https://github.com/GoogleCloudPlatform/knowledge-catalog/compare/" +
              before + "..." + after)
    else:
        print("SPEC unchanged during this update; this is not a compatibility certification.")
    link_path = "okf/vault/KQI"
    if git(target, "ls-files", "--", link_path):
        raise ValueError("Upstream tracks okf/vault/KQI; connection requires manual review.")
    # Keep the machine-specific connection outside upstream commits.
    exclude = Path(git(target, "rev-parse", "--git-path", "info/exclude"))
    if not exclude.is_absolute():
        exclude = target / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    previous = exclude.read_text() if exclude.exists() else ""
    if "/okf/vault/KQI" not in previous.splitlines():
        exclude.write_text(previous + "\n/okf/vault/KQI\n")
    print(connect(target / "okf", vault))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path,
                        help="External upstream checkout; defaults to ../knowledge-catalog-upstream")
    args = parser.parse_args()
    vault = Path(__file__).resolve().parents[1]
    try:
        update(args.checkout or vault.parent / "knowledge-catalog-upstream", vault)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
