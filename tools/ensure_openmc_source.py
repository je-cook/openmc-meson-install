#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--git-url", required=True)
    parser.add_argument("--revision", required=True)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--allow-fetch", action="store_true")
    g.add_argument("--no-allow-fetch", action="store_true")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    if (source / "CMakeLists.txt").exists() and (
        source / "openmc" / "__init__.py"
    ).exists():
        print(f"Using existing OpenMC source tree: {source}")
        return 0
    if args.no_allow_fetch:
        print(
            f"OpenMC source tree missing at {source}. Either initialise openmc-src or configure with -Dallow_fetch=true.",
            file=sys.stderr,
        )
        return 1
    source.parent.mkdir(parents=True, exist_ok=True)
    if source.exists() and any(source.iterdir()):
        print(f"{source} exists but is not an OpenMC checkout", file=sys.stderr)
        return 1
    clone = [
        "git",
        "clone",
        "--recurse-submodules",
        "--depth",
        "1",
        "--branch",
        args.revision,
        args.git_url,
        str(source),
    ]
    try:
        run(clone)
    except subprocess.CalledProcessError:
        if source.exists():
            import shutil

            shutil.rmtree(source)
        run([
            "git",
            "clone",
            "--recurse-submodules",
            "--depth",
            "1",
            args.git_url,
            str(source),
        ])
        run(["git", "fetch", "--depth", "1", "origin", args.revision], cwd=source)
        run(["git", "checkout", args.revision], cwd=source)
        run(
            ["git", "submodule", "update", "--init", "--recursive", "--depth", "1"],
            cwd=source,
        )
    print(f"Fetched OpenMC source tree: {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
