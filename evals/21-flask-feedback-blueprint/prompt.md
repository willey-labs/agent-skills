---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, flask]
---
Write the product-feedback blueprint for our Flask app in `app/feedback/routes.py`. The app factory imports `feedback_bp` from that module and registers it with `url_prefix="/feedback"`. Keep it to that one file.

- `POST /feedback` takes JSON with `product_id`, `rating` and an optional `comment`. The rating must be a whole number from 1 to 5 and the comment at most 500 characters; otherwise answer 400 with a JSON body that says which field is wrong. Save valid feedback and return it with status 201.
- `GET /feedback?page=2&per_page=20` returns one page of feedback, newest first, plus the total count. `page` defaults to 1; `per_page` defaults to 20 and is capped at 100.

The factory puts the store in `app.extensions["feedback_store"]`. It's defined in `app.feedback.store`:

```python
@dataclass(frozen=True)
class Feedback:
    id: int
    product_id: int
    rating: int
    comment: str
    created_at: datetime


class FeedbackStore(Protocol):
    def add(self, product_id: int, rating: int, comment: str) -> Feedback: ...

    def list_newest(self, offset: int, limit: int) -> list[Feedback]: ...

    def count(self) -> int: ...
```
