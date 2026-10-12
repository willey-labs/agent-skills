---
type: llm
focus:
  source: file
  path: app/bookings/router.py
---
The file is a FastAPI router for hotel room bookings. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (guest name rules, past dates, response field names, concurrent requests) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It defines `router` as an `APIRouter` serving `POST /rooms/{room_id}/bookings` and `GET /rooms/{room_id}/bookings`; a router prefix that produces those paths counts.
2. Both endpoints receive the repository through `Depends(get_booking_repository)`, directly or through an `Annotated` alias, rather than building or importing a repository instance.
3. The POST endpoint takes its body as a request model, not a raw `dict` or `Request`.
4. Before adding, the POST endpoint compares the new stay with every booking `list_for_room` returns for that room and answers 409 when any of them overlaps.
5. Two stays overlap exactly when each one checks in before the other checks out (new check-in < existing check-out and existing check-in < new check-out), so checking in on another booking's check-out day is accepted.
6. A booking that doesn't overlap is stored through the repository's `add`, and the endpoint answers 201 with the created booking.
7. The GET endpoint returns the bookings `list_for_room` gives for the requested room.
