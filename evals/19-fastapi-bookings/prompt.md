---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [python, write, fastapi]
---
Add room bookings to our FastAPI hotel app. Write the router in `app/bookings/router.py` and its Pydantic schemas, with their validation, in `app/bookings/schemas.py`. The app already includes `router` from `app.bookings.router`, and the repository below already exists in `app.bookings.repository`, so write only those two files.

- `POST /rooms/{room_id}/bookings` books a room for a guest name, a check-in date and a check-out date, and returns the created booking with status 201. Check-out must be after check-in (422 otherwise). A booking must not overlap another booking of the same room (409 otherwise); checking in on the day another guest checks out is fine.
- `GET /rooms/{room_id}/bookings` lists the room's bookings.

Get the repository with `Depends(get_booking_repository)`:

```python
from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class Booking:
    id: int
    room_id: int
    guest_name: str
    check_in: date
    check_out: date


class BookingRepository(Protocol):
    def list_for_room(self, room_id: int) -> list[Booking]: ...

    def add(self, room_id: int, guest_name: str, check_in: date, check_out: date) -> Booking: ...


def get_booking_repository() -> BookingRepository: ...
```
