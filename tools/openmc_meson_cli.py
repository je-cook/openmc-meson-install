#!/usr/bin/env python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _candidate_binaries() -> list[Path]:
    pkg_dir = Path(__file__).resolve().parent
    lib_dir = pkg_dir / "lib"
    return [
        lib_dir / "openmc_native",
        lib_dir / "openmc",
    ]


def native_executable() -> Path:
    for candidate in _candidate_binaries():
        if candidate.is_file():
            return candidate
    searched = "\n  ".join(str(p) for p in _candidate_binaries())
    manifests = [
        Path(__file__).resolve().parent / "lib" / "_meson_native_manifest.txt",
        Path(__file__).resolve().parent / "lib" / "_meson_bundle_manifest.txt",
    ]
    extra = ""
    for manifest in manifests:
        extra += f"\nManifest exists: {manifest.exists()} at {manifest}"
        if manifest.exists():
            extra += "\n" + manifest.read_text(errors="replace")
    raise RuntimeError(
        "The OpenMC native executable was not found in this wheel. Searched:\n  "
        + searched
        + extra
    )


def _runtime_env(lib_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    lib_dir_s = str(lib_dir)
    if sys.platform == "darwin":
        key = "DYLD_LIBRARY_PATH"
    else:
        key = "LD_LIBRARY_PATH"
    env[key] = lib_dir_s + os.pathsep + env.get(key, "")
    env.setdefault("OPENMC_MESON_LIBDIR", lib_dir_s)
    return env


def main() -> int:
    exe = native_executable()
    lib_dir = exe.parent
    mode = exe.stat().st_mode
    if not (mode & 0o111):
        exe.chmod(mode | 0o755)
    completed = subprocess.run([str(exe), *sys.argv[1:]], env=_runtime_env(lib_dir))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
