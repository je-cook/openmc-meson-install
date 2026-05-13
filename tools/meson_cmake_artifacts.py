#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from _cmake_common import cmake_configure_cmd, print_preflight, run_logged


def find_first(patterns: list[str], roots: list[Path]) -> Path | None:
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                if path.is_file():
                    return path
    return None


def copy_file(src: Path | None, dst: Path, required: bool, label: str) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src is None:
        msg = f"{label}: not found"
        if required:
            raise RuntimeError(msg)
        dst.write_bytes(b"")
        return msg + f" (wrote placeholder {dst})"
    shutil.copy2(src, dst)
    if os.name != "nt":
        dst.chmod(
            dst.stat().st_mode
            | stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IRGRP
            | stat.S_IROTH
        )
    return f"{label}: {src} -> {dst}"


def copy_executable(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if os.name != "nt":
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def candidate_search_roots(build: Path, stage: Path) -> list[Path]:
    roots = [
        stage / "bin",
        build / "bin",
        build,
        stage,
        stage / "lib",
        stage / "lib64",
        build / "lib",
        Path(sys.prefix) / "lib",
    ]
    roots.extend(
        Path(os.environ[env]) / "lib"
        for env in ["CONDA_PREFIX", "VIRTUAL_ENV"]
        if os.environ.get(env)
    )
    roots.extend(
        Path(p)
        for p in [
            "/usr/local/lib",
            "/usr/local/lib64",
            "/usr/lib",
            "/usr/lib64",
            "/usr/lib/x86_64-linux-gnu",
            "/lib/x86_64-linux-gnu",
            "/lib",
        ]
    )
    # CMake often records the actual resolved library path in the cache.
    cache = build / "CMakeCache.txt"
    if cache.exists():
        for m in re.finditer(r"=(/[^\n]+)", cache.read_text(errors="ignore")):
            path = Path(m.group(1).strip())
            if path.is_file():
                roots.append(path.parent)
            elif path.is_dir():
                roots.append(path)
    # Preserve order, remove duplicates.
    out = []
    for r in roots:
        try:
            rr = r.resolve()
        except Exception:
            rr = r
        if rr not in out:
            out.append(rr)
    return out


def find_library(name: str, roots: list[Path]) -> Path | None:
    # Exact basename first.
    for root in roots:
        if root.exists():
            p = root / name
            if p.is_file():
                return p
    # Then recursive search in likely non-system prefixes only.
    recursive_roots = [
        r
        for r in roots
        if str(r).startswith((
            "/usr/local",
            str(Path(sys.prefix)),
            os.environ.get("CONDA_PREFIX", "/never-match"),
        ))
    ]
    for root in recursive_roots:
        if root.exists():
            for p in root.rglob(name):
                if p.is_file():
                    return p
    # Finally ask ldconfig, if available.
    try:
        proc = subprocess.run(
            ["ldconfig", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in proc.stdout.splitlines():
            if name in line and "=>" in line:
                p = Path(line.split("=>", 1)[1].strip())
                if p.is_file():
                    return p
    except Exception:
        pass
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    for a in [
        "source",
        "build",
        "stage",
        "buildtype",
        "generator",
        "stamp-out",
        "native-out",
        "lib-out",
        "fmt-out",
        "pugixml-out",
        "manifest-out",
        "bundle-manifest-out",
    ]:
        p.add_argument("--" + a, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--bundle-runtime-deps", action="store_true")
    g.add_argument("--no-bundle-runtime-deps", action="store_true")
    p.add_argument("--cmake-defs", default="")
    args = p.parse_args()
    source = Path(args.source).resolve()
    build = Path(args.build).resolve()
    stage = Path(args.stage).resolve()
    stamp_out = Path(args.stamp_out).resolve()
    native_out = Path(args.native_out).resolve()
    lib_out = Path(args.lib_out).resolve()
    fmt_out = Path(args.fmt_out).resolve()
    pugixml_out = Path(args.pugixml_out).resolve()
    manifest_out = Path(args.manifest_out).resolve()
    bundle_manifest_out = Path(args.bundle_manifest_out).resolve()
    build.mkdir(parents=True, exist_ok=True)
    stage.mkdir(parents=True, exist_ok=True)
    print_preflight()
    run_logged(
        cmake_configure_cmd(
            source, build, stage, args.buildtype, args.generator, args.cmake_defs
        ),
        build / "cmake-configure.log",
    )
    run_logged(
        ["cmake", "--build", str(build), "--parallel", str(os.cpu_count() or 2)],
        build / "cmake-build.log",
    )
    run_logged(
        ["cmake", "--install", str(build), "--prefix", str(stage)],
        build / "cmake-install.log",
    )
    roots = candidate_search_roots(build, stage)
    native = find_first(["openmc", "openmc.exe"], roots)
    lib = find_first(
        ["libopenmc.so", "libopenmc.so.*", "libopenmc.dylib", "openmc.dll"], roots
    )
    if native is None:
        raise RuntimeError(
            f"Could not find native OpenMC executable. Searched: {[str(r) for r in roots]}"
        )
    if lib is None:
        raise RuntimeError(
            f"Could not find libopenmc shared library. Searched: {[str(r) for r in roots]}"
        )
    copy_executable(native, native_out)
    lib_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lib, lib_out)
    if os.name != "nt":
        lib_out.chmod(
            lib_out.stat().st_mode
            | stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IRGRP
            | stat.S_IROTH
        )
    bundle_lines = []
    if args.bundle_runtime_deps:
        fmt = find_library("libfmt.so.11", roots)
        pugixml = find_library("libpugixml.so.1", roots)
        bundle_lines.extend((
            copy_file(fmt, fmt_out, True, "libfmt.so.11"),
            copy_file(pugixml, pugixml_out, True, "libpugixml.so.1"),
        ))
    else:
        bundle_lines.extend((
            copy_file(None, fmt_out, False, "libfmt.so.11"),
            copy_file(None, pugixml_out, False, "libpugixml.so.1"),
        ))
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    bundle_manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(
        f"source={source}\nbuild={build}\nstage={stage}\nnative_found={native}\nnative_out={native_out}\nlib_found={lib}\nlib_out={lib_out}\n",
        encoding="utf-8",
    )
    bundle_manifest_out.write_text(
        "\n".join(bundle_lines)
        + "\nsearch_roots="
        + repr([str(r) for r in roots])
        + "\n",
        encoding="utf-8",
    )
    stamp_out.write_text("built\n", encoding="utf-8")
    print("Declared Meson artifacts:")
    print(f"  native: {native_out}")
    print(f"  lib:    {lib_out}")
    print(f"  fmt:    {fmt_out}")
    print(f"  pugixml:{pugixml_out}")
    print(f"  log:    {manifest_out}")
    print(f"  bundle: {bundle_manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
