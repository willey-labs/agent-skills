#!/usr/bin/env python3
"""Install the required packages — the mandatory dependency install flow.

In a non-TTY (agent) context, or with --auto-install, the install always
proceeds; on a TTY it confirms first. Falls back to a dedicated venv when the
system Python is externally-managed (PEP 668) so the agent never has to re-run.
Whether the packages ended up available is decided by the caller via
`required_packages_available` (in `_dependencies`).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .dependencies import (
    REQUIRED_PACKAGES,
    check_required_packages,
    managed_venv_has_packages,
    managed_venv_python,
)
from .paths import MANAGED_VENV_DIR


@dataclass
class InstallOutcome:
    """Result of attempting to install the required packages."""
    ok: bool
    message: str
    externally_managed: bool = False


def install_packages(report: dict) -> InstallOutcome:
    """Install the missing required packages via `python -m pip install`.

    Uses `--user` outside virtualenvs to avoid touching the system Python. On a
    PEP 668 externally-managed refusal, returns `externally_managed=True` so the
    caller can fall back to a dedicated venv instead of giving up.
    """
    if not report["missing_packages"]:
        return InstallOutcome(ok=True, message="nothing to install")
    if not report["pip_command"]:
        return InstallOutcome(
            ok=False,
            message="pip is unavailable — install pip first, then re-run bootstrap.",
        )

    cmd = [sys.executable, "-m", "pip", "install"]
    if not report["in_venv"]:
        cmd.append("--user")
    cmd.extend(report["missing_packages"])

    print(f"  Running: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=300
        )
        last_line = proc.stdout.strip().splitlines()[-1] if proc.stdout else "installed"
        return InstallOutcome(ok=True, message=last_line)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if "externally-managed" in stderr.lower() or "externally managed" in stderr.lower():
            return InstallOutcome(
                ok=False,
                message="pip refused to install into an externally-managed Python (PEP 668).",
                externally_managed=True,
            )
        return InstallOutcome(ok=False, message=f"pip install failed:\n{stderr[-500:]}")
    except subprocess.TimeoutExpired:
        return InstallOutcome(ok=False, message="pip install timed out after 300s")


def create_managed_venv() -> tuple[Path | None, str]:
    """Create a dedicated venv beside the hooks and install the required packages.

    The escape hatch when the running interpreter is externally-managed (PEP
    668): it lets the required install finish in a single run instead of asking
    the user to build a venv and re-bootstrap. Returns (venv_python, message);
    venv_python is None on failure (the caller then surfaces a blocking issue).
    """
    venv_python = managed_venv_python()
    packages = [package for _module, package in REQUIRED_PACKAGES]
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(MANAGED_VENV_DIR)],
            check=True, capture_output=True, text=True, timeout=120,
        )
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", *packages],
            check=True, capture_output=True, text=True, timeout=300,
        )
        return venv_python, f"venv at {MANAGED_VENV_DIR} (required packages installed)"
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "").strip()[-500:]
        return None, f"venv setup failed:\n{detail}"
    except subprocess.TimeoutExpired:
        return None, "venv setup timed out after 300s"


def _print_install_declined(report: dict) -> None:
    """Print the next step after an interactive decline. The install is
    required, so a decline leaves the host non-ready — the caller surfaces the
    blocking issue; this just tells the user how to complete it later."""
    packages = " ".join(report["missing_packages"])
    print(
        f"  These packages are required to run the skill's checks. Re-run with "
        f"--auto-install, or `pip install {packages}` manually, then re-run "
        f"bootstrap."
    )


def _build_managed_venv(reason: str) -> Path | None:
    """Create the dedicated venv (announcing `reason`) and report it. Returns its
    interpreter path, or None if creation failed (the caller then surfaces a
    blocking issue or falls back)."""
    print(f"  {reason}")
    venv_python, message = create_managed_venv()
    if venv_python is not None:
        print(f"  Install OK: {message}\n  Hooks will use this venv's Python.\n")
    else:
        print(f"  {message}")
    return venv_python


def _run_package_install(report: dict) -> tuple[dict, Path | None]:
    """Run the required install; fall back to a managed venv on PEP 668. Returns
    the (possibly refreshed) report and the venv interpreter path (None if
    unused). The caller decides whether the packages ended up available."""
    outcome = install_packages(report)
    if outcome.ok:
        print(f"  Install OK: {outcome.message}\n")
        # Re-probe just the package fields rather than rebuilding the whole
        # report — the rest of the host state can't have changed mid-run.
        packages_ok, missing = check_required_packages()
        return {**report, "packages_ok": packages_ok, "missing_packages": missing}, None
    if outcome.externally_managed:
        return report, _build_managed_venv(
            "System Python is externally-managed (PEP 668). Creating a dedicated "
            "venv so the required packages install in this one run…"
        )
    print(f"  Install failed: {outcome.message}")
    print(
        f"  Install manually with: {sys.executable} -m pip install "
        + " ".join(report["missing_packages"])
    )
    return report, None


def prompt_user_for_install(missing: list[str]) -> bool:
    """Ask the user interactively whether to install the required packages.
    Returns True to proceed, False on an explicit decline.

    If stdin is not a TTY (agent invocation), returns True — the packages are
    mandatory and there's no one to prompt, so the install proceeds.
    """
    if not sys.stdin.isatty():
        return True
    pkg_list = ", ".join(missing)
    print(
        f"\n  Required: install {pkg_list}?"
    )
    print(
        f"  The skill's hooks need these to run their checks (currently the "
        f"tree-sitter grammars behind FN-001/FN-005/OD-004 on TS/JS)."
    )
    print(f"  The skill won't wire its hooks until these load.")
    try:
        answer = input("  Install now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("", "y", "yes")


def ensure_required_packages(report: dict, args: argparse.Namespace) -> tuple[dict, Path | None]:
    """Install the required packages (see REQUIRED_PACKAGES) when any is missing.

    The single entry point for the install step. Falls back to a managed venv
    when the system Python is externally-managed so the agent never has to
    re-run. Returns the (possibly refreshed) report and a managed-venv
    interpreter path (None when no venv was created).
    """
    # A previous run already built the managed venv with the packages: reuse it
    # so the hooks stay pointed at the only interpreter that has them, but don't
    # reinstall or print the restart nag. Without this, a re-run would rewire the
    # hooks to a system Python that lacks them.
    if managed_venv_has_packages():
        return report, managed_venv_python()
    if not report["missing_packages"]:
        return report, None
    should_install = args.auto_install or prompt_user_for_install(report["missing_packages"])
    if not should_install:
        _print_install_declined(report)
        return report, None
    return _run_package_install(report)


def _prompt_create_global_venv() -> bool:
    """Confirm creating the dedicated global venv. Non-TTY (agent) proceeds."""
    if not sys.stdin.isatty():
        return True
    print(
        "\n  Global install: create a dedicated coding-standards venv for the hooks?"
    )
    print(
        "  It keeps the skill's tree-sitter independent of whatever python3 is "
        "first on your PATH, so the hooks don't break if that interpreter changes."
    )
    try:
        answer = input("  Create now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("", "y", "yes")


def ensure_global_venv(report: dict, args: argparse.Namespace) -> tuple[dict, Path | None]:
    """Global-scope install strategy: own a dedicated coding-standards venv.

    Reuse it if it already has the packages; otherwise build it. Unlike the
    project-scope path, this does NOT pin whatever interpreter is first on PATH
    (e.g. a transient tool venv) — global `settings.json` isn't shared, so an
    absolute venv path is the stable choice. If the user declines (TTY), we fall
    back to the report's interpreter state and the caller's gate decides.
    """
    if managed_venv_has_packages():
        return report, managed_venv_python()
    if not (args.auto_install or _prompt_create_global_venv()):
        print(
            "  Skipped the dedicated venv — falling back to this interpreter. "
            "Re-run with --auto-install to create the venv."
        )
        return report, None
    venv_python = _build_managed_venv(
        "Global install — creating a dedicated coding-standards venv so the hooks "
        "don't depend on whatever python3 is first on PATH…"
    )
    return report, venv_python
