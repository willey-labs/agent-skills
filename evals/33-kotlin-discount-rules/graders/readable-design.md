---
type: llm
focus:
  source: file
  path: src/main/kotlin/com/acme/pricing/DiscountService.kt
---
Grade the design of this file. Ignore whether the calculation is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `amt`, `qty`, `pct`, `disc`, `tmp`, `res`, `val`, and no single-letter names except a lambda parameter (including `it`) or loop variable used within one or two lines.
2. No function body is longer than 25 lines.
3. Nothing is more elaborate than three fixed rule kinds need: no rule registry, Factory, Spring bean per rule, or plugin mechanism. A sealed class or interface with one subtype per rule kind is fine, whether the service uses `when` or each subtype computes its own discount.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments (KDoc). Apart from doc comments directly above the declaration they document, no comment runs past one line.
