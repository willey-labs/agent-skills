#!/usr/bin/env python3
"""The pinned corpus for the false-block-rate eval.

Each entry is an idiomatic open-source repo for one supported language/framework,
pinned to a commit SHA so the measurement is repeatable. SHAs resolved with
`git ls-remote <url> HEAD`.

The corpus is official templates and canonical references — clean code a reviewer
would call idiomatic — which biases the rate toward stance blocks over true
positives. Frameworks with no entry are listed in UNCOVERED_FRAMEWORKS so the rate
isn't mistaken for full coverage; add a RepoSpec to cover one.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepoSpec:
    """One corpus repo, pinned for reproducibility."""

    name: str
    url: str
    ref: str  # immutable commit SHA — `git ls-remote <url> HEAD` at build time
    framework: str
    language: str
    extensions: tuple[str, ...]  # source suffixes to scan in this repo
    note: str = ""


# Per-repo extension sets. A repo is scanned for its primary language's files
# only — the hooks self-filter by suffix, but scanning only the relevant files
# keeps the sample focused on the language we mean to measure.
_TS = (".ts", ".tsx")
_PY = (".py",)
_GO = (".go",)
_CS = (".cs",)
_PHP = (".php",)
_JAVA = (".java",)


CORPUS: tuple[RepoSpec, ...] = (
    RepoSpec(
        name="taxonomy",
        url="https://github.com/shadcn-ui/taxonomy.git",
        ref="298a8857c7128a0d121e7f699dfd729f23b3966d",
        framework="nextjs",
        language="ts",
        extensions=_TS,
        note="Next.js App Router reference app by shadcn",
    ),
    RepoSpec(
        name="nestjs-typescript-starter",
        url="https://github.com/nestjs/typescript-starter.git",
        ref="c4d9330f5513eda0fb5df594f6b34a11fde1a934",
        framework="nestjs",
        language="ts",
        extensions=_TS,
        note="Official NestJS starter",
    ),
    RepoSpec(
        name="full-stack-fastapi-template",
        url="https://github.com/fastapi/full-stack-fastapi-template.git",
        ref="cd83fc10ca20393e9ee50e3005e170c6929e047e",
        framework="fastapi",
        language="py",
        extensions=_PY,
        note="Official FastAPI full-stack template",
    ),
    RepoSpec(
        name="django",
        url="https://github.com/django/django.git",
        ref="189c2d2ce58482db5c09d8b1e1464d1456dc9bab",
        framework="django",
        language="py",
        extensions=_PY,
        note="Django framework source — canonical idiomatic Python",
    ),
    RepoSpec(
        name="gin",
        url="https://github.com/gin-gonic/gin.git",
        ref="d75fcd4c9ab260e5225de590f1f0f8c0e0e12d11",
        framework="go-http",
        language="go",
        extensions=_GO,
        note="Popular Go HTTP framework — idiomatic Go",
    ),
    RepoSpec(
        name="clean-architecture",
        url="https://github.com/jasontaylordev/CleanArchitecture.git",
        ref="43831e20374677b81f93bb08923eff3245b7195f",
        framework="csharp",
        language="cs",
        extensions=_CS,
        note="Widely-cited .NET clean-architecture reference",
    ),
    RepoSpec(
        name="laravel",
        url="https://github.com/laravel/laravel.git",
        ref="18b3074796f4c2a17955440ec36033be81b71715",
        framework="laravel",
        language="php",
        extensions=_PHP,
        note="Canonical Laravel application skeleton",
    ),
    RepoSpec(
        name="spring-petclinic",
        url="https://github.com/spring-projects/spring-petclinic.git",
        ref="a2c2ef994340d3970eb6db51247456a51bb161f8",
        framework="spring-boot",
        language="java",
        extensions=_JAVA,
        note="Canonical Spring Boot sample",
    ),
)


# Frameworks the hooks cover that have NO corpus entry yet. The runner prints
# this so a reader never mistakes the measured rate for full coverage.
UNCOVERED_FRAMEWORKS: tuple[str, ...] = (
    "vue-nuxt (.vue SFC <script> extraction)",
    "svelte (.svelte SFC <script> extraction)",
    "react-native",
    "nativescript",
    "cocos-creator",
    "kotlin (spring-boot Kotlin flavour)",
    "flask",
    "node-express",
    "vanilla-js",
)


def is_test_file(name: str) -> bool:
    """True for a test/spec file by filename convention across the corpus langs.

    Test code is excluded from the idiomatic-application-source sample for the
    same reason the god-file hook exempts it: it's held to a different bar, so a
    block there isn't evidence about the rate on real app code. Dir-level skips
    (tests/, spec/) miss files like Go's `foo_test.go` that live beside source.
    """
    lower = name.lower()
    stem = name.rsplit(".", 1)[0]
    if lower.endswith("_test.go"):
        return True
    if ".test." in lower or ".spec." in lower:
        return True
    if lower.startswith("test_") or lower.endswith("_test.py") or lower == "conftest.py":
        return True
    if stem.lower() in {"test", "tests"}:
        return True
    return stem.endswith(("Test", "Tests"))  # PHPUnit / JUnit / xUnit class files


# Directory names skipped during scanning: tests/examples/docs aren't the
# idiomatic *application* source whose false-block rate we care about, and
# build/dependency dirs are already hook-excluded but skipping them saves work.
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        "tests",
        "test",
        "__tests__",
        "testing",
        "e2e",
        "spec",
        "specs",
        "examples",
        "example",
        "docs",
        "doc",
        "migrations",
    }
)
