---
type: llm
focus:
  source: file
  path: app/bookings/schemas.py
---
The file holds the Pydantic schemas for booking a hotel room. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (guest name rules, past dates, response models and their fields) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. A request model holds a guest name, a check-in `date` and a check-out `date`.
2. That model rejects a check-out on or before the check-in with a Pydantic validator (`field_validator`, `model_validator`, or the v1 `validator` / `root_validator`) that raises an error Pydantic reports as a validation error (`ValueError`, `AssertionError` or `PydanticCustomError`), so FastAPI answers 422. A check-out equal to the check-in is rejected.
