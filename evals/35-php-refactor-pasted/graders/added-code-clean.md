---
type: llm
focus:
  source: file
  path: src/Shipping/RateCalculator.php
---
The user pasted `RateCalculator::calculate(mixed $parcel, string $strZone, bool $bExpress, string $strCoupon = ''): float` and asked for an oversize surcharge. Code carried over from the paste unchanged is not judged. If any parameter of `calculate` was renamed, added, removed, reordered or retyped, the signature counts as rewritten and is judged like new code. Grade only code the agent added or rewrote: the surcharge logic, any new classes, methods, properties, constants or variables, and a rewritten signature. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. No new name uses a type prefix such as `$str`, `$arr`, `$int`, `$flt`, `$b`, `$obj` followed by a capital letter.
2. No new method, and no rewritten `calculate` signature, takes 5 or more parameters. The promoted constructor properties of a class that groups the caller's inputs are fields, not parameters, for this claim.
3. No new or rewritten declaration (parameter, return or property type) uses `mixed`.
4. New names say what they hold or do: no abbreviations such as `$dim`, `$len`, `$tmp`, `$res`, `$val`, `$max` used beyond one or two lines.
5. Nothing is more elaborate than one surcharge needs: no surcharge-rule interface, pipeline or Strategy, Factory, or registry. A small parcel value object, a constant and an enum for zones are fine.
6. No `//` comment the agent added restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments. Apart from doc comments directly above the declaration they document, no comment runs past one line.
