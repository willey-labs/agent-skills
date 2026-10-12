---
type: llm
focus:
  source: file
  path: app/feedback/routes.py
---
The file is a Flask blueprint for product feedback, which the app factory registers with `url_prefix="/feedback"`. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (`product_id` checks, the comment's type, page values below 1, non-numeric `page` or `per_page`, the wording of errors, response field names) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It defines a `Blueprint` named `feedback_bp` with a POST route and a GET route at the blueprint's root (`""` or `"/"`).
2. Both handlers get the store from `current_app.extensions["feedback_store"]`, not from a module-level instance.
3. POST answers 400 for a missing rating, a rating that is not a number, a rating with a fractional part such as 4.5, and a whole number outside 1 to 5. Converting with `int()` in a way that turns 4.5 into 4 fails this claim.
4. POST answers 400 for a comment longer than 500 characters, and accepts feedback with no comment.
5. Each 400 has a JSON body that identifies the invalid field.
6. Valid feedback is saved with the store's `add` and returned as JSON with status 201.
7. GET reads `page` and `per_page` from the query string with defaults 1 and 20, caps `per_page` at 100, and calls `list_newest` with offset `(page - 1) * per_page` and limit `per_page`.
8. GET returns that page's feedback and the total from `count()`.
