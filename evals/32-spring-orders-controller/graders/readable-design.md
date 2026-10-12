---
type: llm
focus:
  source: file
  path: src/main/java/com/acme/orders/OrderService.java
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `qty`, `avail`, `tmp`, `res`, `val`, `ord`, and no single-letter names except a loop variable or lambda parameter used within one or two lines.
2. No method body is longer than 25 lines.
3. Nothing is more elaborate than two operations need: no generic `BaseService` or `BaseRepository`, Strategy/Factory pattern, or domain events. An exception class per failure and request/response records are fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments (Javadoc). Apart from doc comments directly above the declaration they document, no comment runs past one line.
