#!/usr/bin/env python3
"""Regression test — FN-005 C# 12 primary-constructor carve-out (ISS-008).

A primary constructor on a class/struct (`class Foo(dep1, …, dep5)`) carries DI
dependencies, not hot-path arguments — exempt like a classic constructor and like
records. An ordinary 5-param method, and a method whose name merely contains
"Class", must still block.

    python3 hooks/tests/test-csharp-primary-ctor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report  # noqa: E402

CS = "block-csharp-violations.py"

CASES: list[Case] = [
    Case("class primary ctor 5 deps passes", CS, "/tmp/x/OrdersService.cs",
         "public class OrdersService(IOrdersRepo repo, IClock clock, IBus bus, "
         "ILogger<OrdersService> log, IMapper mapper) { }\n", block=False),
    Case("struct primary ctor 5 deps passes", CS, "/tmp/x/Vec.cs",
         "public struct Vec(double a, double b, double c, double d, double e) { }\n", block=False),
    Case("record 5 members passes", CS, "/tmp/x/Dto.cs",
         "public record Dto(int A, int B, int C, int D, int E);\n", block=False),
    Case("ordinary 5-param method blocks", CS, "/tmp/x/Svc.cs",
         "public class Svc {\n  public void Foo(int a, int b, int c, int d, int e) { }\n}\n",
         block=True, rule="FN-005"),
    Case("method named ProcessClass still blocks", CS, "/tmp/x/P.cs",
         "public class P {\n  public void ProcessClass(int a, int b, int c, int d, int e) { }\n}\n",
         block=True, rule="FN-005"),
    Case("classic ctor 5 deps passes", CS, "/tmp/x/Old.cs",
         "public class Old {\n  public Old(IA a, IB b, IC c, ID d, IE e) { }\n}\n", block=False),
]


if __name__ == "__main__":
    sys.exit(report("csharp-primary-ctor", CASES))
