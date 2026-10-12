---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, fix, none]
---
The "Open now" badge on our store page is wrong in two ways. In the afternoon it starts saying we're closed hours before closing time (the servers run on UTC; the store is in New York). And at exactly closing time it still says we're open. Here's the function. Fix it and save it as `store_hours.py`.

```python
from datetime import datetime, time
from zoneinfo import ZoneInfo

STORE_TIMEZONE = ZoneInfo("America/New_York")

OPENING_HOURS = {
    0: (time(9, 0), time(21, 0)),
    1: (time(9, 0), time(21, 0)),
    2: (time(9, 0), time(21, 0)),
    3: (time(9, 0), time(21, 0)),
    4: (time(9, 0), time(22, 0)),
    5: (time(10, 0), time(22, 0)),
    6: (time(11, 0), time(18, 0)),
}


def is_store_open():
    now = datetime.now()
    opens_at, closes_at = OPENING_HOURS[now.weekday()]
    return opens_at <= now.time() <= closes_at
```
