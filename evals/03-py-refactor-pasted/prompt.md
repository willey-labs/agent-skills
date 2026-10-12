---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, refactor, none]
---
Here's a function from our reporting script. Add an option so it can output CSV instead of plain text (the unused last parameter was meant for that), and save the result as `report_builder.py`.

```python
def build_report(strTitle, lstRows, intLimit, bIncludeTotals, strFormat):
    # loop over the rows
    out = []
    for r in lstRows[:intLimit]:
        try:
            out.append(f"{r['name']}: {r['amount']}")
        except:
            pass
    # add totals if needed
    if bIncludeTotals:
        out.append("TOTAL: " + str(sum(r['amount'] for r in lstRows[:intLimit])))
    return strTitle + "\n" + "\n".join(out)
```
