#!/usr/bin/env python
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def build_type(bt: str) -> str:
    return {
        "plain": "Release",
        "debug": "Debug",
        "debugoptimized": "RelWithDebInfo",
        "release": "Release",
        "minsize": "MinSizeRel",
        "custom": "Release",
    }.get(bt, "Release")


def split_defs(defs: str) -> list[str]:
    return [item for item in defs.split(",") if item]


def append_env_cmake_args(cmd: list[str]) -> list[str]:
    env_args = os.environ.get("CMAKE_ARGS", "").strip()
    if env_args:
        cmd.extend(shlex.split(env_args))
    prefixes = []
    if sys.prefix:
        prefixes.append(sys.prefix)
    if os.environ.get("CONDA_PREFIX"):
        prefixes.append(os.environ["CONDA_PREFIX"])
    if not any(arg.startswith("-DCMAKE_PREFIX_PATH=") for arg in cmd):
        unique = []
        for p in prefixes:
            if p and p not in unique:
                unique.append(p)
        if unique:
            cmd.append("-DCMAKE_PREFIX_PATH=" + os.pathsep.join(unique))
    if os.environ.get("HDF5_ROOT") and not any(
        arg.startswith("-DHDF5_ROOT=") for arg in cmd
    ):
        cmd.append("-DHDF5_ROOT=" + os.environ["HDF5_ROOT"])
    return cmd


def print_preflight() -> None:
    print("--- OpenMC meson wrapper preflight ---", flush=True)
    print(f"Python: {sys.executable}", flush=True)
    print(f"sys.prefix: {sys.prefix}", flush=True)
    for tool in ["cmake", "ninja", "git", "h5cc", "h5pcc", "pkg-config"]:
        print(f"{tool}: {shutil.which(tool) or 'not found on PATH'}", flush=True)
    for var in ["HDF5_ROOT", "CMAKE_PREFIX_PATH", "CMAKE_ARGS", "CONDA_PREFIX"]:
        if os.environ.get(var):
            print(f"{var}={os.environ[var]}", flush=True)
    print("--------------------------------------", flush=True)


def run_logged(cmd: list[str], log_file: Path) -> None:
    print("+ " + " ".join(shlex.quote(c) for c in cmd), flush=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    log_file.write_text(proc.stdout, encoding="utf-8")
    print(proc.stdout, end="", flush=True)
    if proc.returncode != 0:
        print("\nERROR: command failed. Full log:", log_file, file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def cmake_configure_cmd(
    source: Path, build: Path, stage: Path, buildtype: str, generator: str, defs: str
) -> list[str]:
    cmd = [
        "cmake",
        "-S",
        str(source),
        "-B",
        str(build),
        "-G",
        generator,
        f"-DCMAKE_BUILD_TYPE={build_type(buildtype)}",
        f"-DCMAKE_INSTALL_PREFIX={stage}",
    ]
    cmd.extend(
        item if item.startswith("-D") else f"-D{item}" for item in split_defs(defs)
    )
    return append_env_cmake_args(cmd)
