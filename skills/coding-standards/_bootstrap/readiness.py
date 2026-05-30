#!/usr/bin/env python3
"""Machine-readiness check — reports the state of the host on every run.

Detects the Python interpreter/command, pip, virtualenv, platform, and whether
every required package imports, then assembles a structured report and prints a
human-readable summary. Cross-platform: Windows, macOS, Linux.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

from .dependencies import MIN_PYTHON, REQUIRED_PACKAGES, check_required_packages


def detect_python_command() -> str:
    """Find a `python` invocation that works across Linux / macOS / Windows.

    Returns the command to put in settings.json hook entries. Prefers
    `python3` (canonical on Linux/macOS), falls back to `python` (Windows),
    then to the absolute path of the currently-running interpreter as a
    last resort.
    """
    for candidate in ("python3", "python"):
        if shutil.which(candidate):
            return candidate
    # No `python`/`python3` on PATH — use the absolute path to this script's
    # interpreter. Works in venvs and on systems where Python is installed
    # in a non-standard location.
    return sys.executable


def _probe_python_version(path: str) -> tuple[int, int] | None:
    """(major, minor) of the interpreter at `path`, or None if it won't run."""
    try:
        proc = subprocess.run(
            [path, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        major, minor = proc.stdout.split()[:2]
        return int(major), int(minor)
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def find_compatible_python() -> str | None:
    """Path to an interpreter >= MIN_PYTHON, or None if none is on the machine.

    Prefers the running interpreter when it already qualifies; otherwise scans
    PATH for versioned `python3.x` binaries (newest first), then the generic
    `python3`/`python`. NEVER installs a Python — it only locates one already
    present, so a host with, say, a 3.9 default but 3.12 also installed can be
    auto-recovered instead of blocked. Returns None when nothing qualifies (the
    caller then blocks: bootstrap can't and won't install an interpreter).
    """
    if sys.version_info[:2] >= MIN_PYTHON:
        return sys.executable
    floor = MIN_PYTHON[1]
    names = [f"python3.{minor}" for minor in range(floor + 10, floor - 1, -1)]
    names += ["python3", "python"]
    seen: set[str] = set()
    for name in names:
        path = shutil.which(name)
        if not path:
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        version = _probe_python_version(path)
        if version is not None and version >= MIN_PYTHON:
            return path
    return None


def detect_pip_command() -> str | None:
    """Return the canonical pip invocation (`<python> -m pip`).

    Using `<python> -m pip` instead of `pip` ensures we install into the
    same interpreter that's running the hooks. Returns None if pip isn't
    importable at all (rare — typical only on stripped-down distros).
    """
    py = sys.executable
    try:
        subprocess.run(
            [py, "-m", "pip", "--version"],
            check=True, capture_output=True, timeout=10,
        )
        return f"{py} -m pip"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def in_virtualenv() -> bool:
    """Detect whether the current Python is inside an isolated environment.

    True for venv/virtualenv (base_prefix != prefix, or the legacy real_prefix)
    AND for conda/mamba. Conda does NOT reliably set base_prefix != prefix, so
    it's detected via the CONDA_PREFIX / CONDA_DEFAULT_ENV env markers. False
    for bare system Python. Used to decide whether to add `--user` to pip
    install — inside ANY of these, `--user` errors or installs to the wrong
    place, so it must be omitted.
    """
    if hasattr(sys, "real_prefix"):
        return True
    if hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix:
        return True
    # conda/mamba often don't set base_prefix != prefix; fall back to env vars.
    if os.environ.get("CONDA_PREFIX") or os.environ.get("CONDA_DEFAULT_ENV"):
        return True
    return False


def readiness_report() -> dict:
    """Return a structured readiness report.

    Keys:
      python_version_ok: bool
      python_version:    tuple[int, int, int]
      python_command:    str (the command to put in settings.json)
      pip_command:       str | None
      in_venv:           bool
      platform:          str ('linux' | 'darwin' | 'windows' | other)
      packages_ok:       bool (every REQUIRED_PACKAGES entry is importable)
      missing_packages:  list[str] (pip names of the missing ones; also the
                         auto-install list)
      blocking_issues:   list[str] (deal-breakers that prevent skill from working)
    """
    py_version = sys.version_info[:3]
    py_ok = py_version >= MIN_PYTHON
    py_cmd = detect_python_command()
    pip_cmd = detect_pip_command()
    venv = in_virtualenv()
    plat = sys.platform  # 'linux', 'darwin', 'win32'
    packages_ok, missing = check_required_packages()

    blocking: list[str] = []
    if not py_ok:
        # If this fires, the re-exec fallback already searched PATH and found no
        # 3.10+ interpreter on the machine — bootstrap can't install one.
        blocking.append(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required (the required "
            f"packages, e.g. the tree-sitter grammars, need it); found "
            f"{py_version[0]}.{py_version[1]}.{py_version[2]} and no newer "
            f"interpreter on this machine — install Python "
            f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ and re-run."
        )

    return {
        "python_version_ok": py_ok,
        "python_version": py_version,
        "python_command": py_cmd,
        "pip_command": pip_cmd,
        "in_venv": venv,
        "platform": plat,
        "platform_pretty": platform.platform(),
        "packages_ok": packages_ok,
        "missing_packages": missing,
        "blocking_issues": blocking,
    }


def print_readiness(report: dict) -> None:
    """Print a human-readable readiness summary."""
    plat_map = {"linux": "Linux", "darwin": "macOS", "win32": "Windows"}
    plat = plat_map.get(report["platform"], report["platform"])
    py = ".".join(str(x) for x in report["python_version"])
    venv = " (venv)" if report["in_venv"] else ""

    print("coding-standards readiness check:")
    py_mark = "OK" if report["python_version_ok"] else "FAIL"
    print(f"  Python {py}{venv}                 [{py_mark}]")
    # Scope decides which interpreter the hooks run under: project keeps the
    # portable PATH name (committed settings.json works across teammates),
    # global uses a dedicated coding-standards venv (built/reused at install,
    # independent of whatever python3 is first on PATH). Readiness runs before
    # scope is known, so preview both.
    print(
        f"  Hook interpreter: project scope -> {report['python_command']}, "
        f"global scope -> dedicated coding-standards venv"
    )
    pip_mark = "OK" if report["pip_command"] else "MISSING"
    pip_str = report["pip_command"] or "(not found)"
    print(f"  pip: {pip_str:<37} [{pip_mark}]")
    print(f"  Platform: {plat:<30} [{report['platform_pretty']}]")
    total = len(REQUIRED_PACKAGES)
    if report["packages_ok"]:
        print(f"  Required packages ({total}): all present  [OK]")
    else:
        present = total - len(report["missing_packages"])
        print(f"  Required packages ({present}/{total} present): missing [installing]")
        for pkg in report["missing_packages"]:
            print(f"    - {pkg}")
