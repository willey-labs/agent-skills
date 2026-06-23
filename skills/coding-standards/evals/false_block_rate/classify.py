#!/usr/bin/env python3
"""Record a verdict on each scanned hard block.

Reads `blocks.json` and writes `blocks-classified.json` so the rate is repeatable
rather than re-judged each run. Verdicts are per (repo, rule) cluster because the
blocked pattern is uniform within a cluster (verified by reading the sampled code).

Verdicts:
  - "tp"             — a block a reviewer would accept as a real violation.
  - "fp" + "misfire" — the regex/AST matched something that isn't an instance of
                       the pattern (a bug).
  - "fp" + "stance"  — the match is correct, but it blocks idiomatic code on a
                       deliberate rule position (e.g. Go `any`, `utils.*`).

A (repo, rule) with no entry here is marked "unclassified" so the report warns
instead of scoring it silently.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# (repo, rule_code) -> (verdict, fp_kind, reason). fp_kind is "" for a tp.
_VERDICTS: dict[tuple[str, str], tuple[str, str, str]] = {
    ("gin", "OD-006"): (
        "fp", "stance",
        "idiomatic Go `any`/`interface{}` for binding/JSON; the match is real, the OD-006 ban is the stance",
    ),
    ("full-stack-fastapi-template", "OD-006"): (
        "fp", "stance",
        "non-route `Any` in the official template (config `dict[str, Any]`, crud `-> Any`); the route-handler "
        "`-> Any` exemption deliberately does NOT cover these — debatable, a stricter setup could tighten them",
    ),
    ("clean-architecture", "ST-005"): (
        "fp", "stance",
        "`.NET Common/` cross-cutting folder is the canonical clean-architecture layout",
    ),
    ("gin", "FN-005"): (
        "tp", "",
        "Go function with 4+ parameters — the mental-load smell FN-005 targets",
    ),
    ("spring-petclinic", "FN-005"): (
        "fp", "stance",
        "Spring MVC handler method with framework params (@Valid, BindingResult, RedirectAttributes) — framework boundary, like the Express/FastAPI carve-outs the skill already ships",
    ),
    # ("django", "OD-004") removed: the P2 tightening — OD-004 now fires only at
    # >=2 accessors (_py_ast.py / _ts_node_checks.py) — drove this cluster to 0 hits
    # on the pinned corpus (re-scan over the same 150-file sample). The earlier
    # "over-fires on ordinary OOP" false positives (one @property + one method) no
    # longer occur. Re-add a verdict here only if a future detector change reopens it.
    ("django", "EH-002"): (
        "tp", "",
        "`except Exception: pass` swallows ALL exceptions with no inline-comment escape — the case EH-002 exists for",
    ),
    ("taxonomy", "OD-006"): (
        "tp", "",
        "`as any` type assertion — the escape hatch OD-006 targets",
    ),
    ("taxonomy", "ST-005"): (
        "fp", "stance",
        "`lib/utils.ts` is the shadcn/Next convention; deliberate ST-005 ban",
    ),
    ("full-stack-fastapi-template", "ST-005"): (
        "fp", "stance",
        "`utils.py` ships in the official FastAPI template; deliberate ST-005 ban",
    ),
    ("gin", "ST-005"): (
        "fp", "stance",
        "`utils.go` — deliberate ST-005 ban on a name common in Go",
    ),
}

# ST-008 is judged by declaration count, not a flat cluster verdict: a genuinely
# huge file is a real god-file; a cohesive file just over the blunt 10-decl proxy
# is the "accepted exemption" case the skill's own Review mode describes.
_ST008_GODFILE_MIN = 24


def _st008_verdict(message: str) -> tuple[str, str, str]:
    match = re.search(r"(\d+) behavioral", message)
    count = int(match.group(1)) if match else 0
    if count >= _ST008_GODFILE_MIN:
        return "tp", "", f"{count} top-level declarations — a genuine god-file doing many jobs"
    return (
        "fp", "stance",
        f"{count} declarations, just over the blunt 10-decl proxy; a cohesive file the skill's Review mode "
        "anticipates as an accepted exemption",
    )


def classify_block(block: dict[str, object]) -> dict[str, object]:
    repo = str(block.get("repo"))
    rule = str(block.get("rule_code"))
    if rule == "ST-008":
        verdict, kind, reason = _st008_verdict(str(block.get("message")))
    else:
        verdict, kind, reason = _VERDICTS.get((repo, rule), ("unclassified", "", "no verdict rule for this cluster"))
    return {**block, "verdict": verdict, "fp_kind": kind, "verdict_reason": reason}


def classify_all(blocks_path: Path, out_path: Path) -> int:
    data = json.loads(blocks_path.read_text(encoding="utf-8"))
    hard = [classify_block(b) for b in data if isinstance(b, dict) and not b.get("is_advisory")]
    out_path.write_text(json.dumps(hard, indent=2), encoding="utf-8")
    unresolved = sum(1 for b in hard if b["verdict"] == "unclassified")
    print(f"classified {len(hard)} hard blocks -> {out_path}")
    if unresolved:
        print(f"WARNING: {unresolved} blocks unclassified (add a verdict rule)")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("usage: classify.py <blocks.json> <blocks-classified.json>")
        sys.exit(1)
    sys.exit(classify_all(Path(sys.argv[1]), Path(sys.argv[2])))
