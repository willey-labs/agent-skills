# Comments

Language-agnostic rules for comments and docstrings. A comment is the one part of a file the compiler never checks, so it rots silently — the only comment worth its upkeep is one the code itself cannot say. This is also where machine-generated code betrays itself most: narrating every line, restating every signature, sprinkling `Note:` / `Important:` preambles. Clean code reads like a person wrote it on purpose.

**Enforcement:** these are **review-only** — no write-time hook. Narration can't be told from a legitimate explanatory comment by regex without a false-positive rate far above the ~1% bar a hard block needs (`AGENTS.md`), so the judgement lives in review (Worker 2). They are still must-fix violations like any other rule — not a soft tier. (The one comment concern that *is* hooked is FMT-005's commented-out-code advisory; CM-* is about prose, not disabled code.)

---

## CM-001 — Don't narrate the code

A comment that restates what the next line plainly does is pure noise — the reader can read the line. It adds upkeep (it drifts when the line changes) and buries the rare comment that matters under ones that don't.

```ts
// Bad — every comment just reads the line aloud
// loop over the users
for (const user of users) {
  // skip inactive users
  if (!user.isActive) continue;
  // add the user's total to the sum
  sum += user.total;
}

// Good — no narration; the names already say it
for (const user of activeUsers) {
  sum += user.total;
}
```

**Test:** delete the comment. If nothing is lost — the code says the same thing — it was narration. Delete it for real.

---

## CM-002 — A comment that explains *what* is a naming bug

If you need a comment to explain what a variable or function *is*, the name failed (see `naming.md` NM-001). Fix the name or extract a well-named function; don't paper over a weak name with a sentence.

```python
# Bad — the comment is doing the name's job
d = (end - start).days  # elapsed time in days

# Good — the name carries the meaning, no comment needed
elapsed_days = (end - start).days
```

```python
# Bad — a comment heading a block that wants to be a function
# validate the order, then charge the customer
if not order.items: raise ...
if order.total <= 0: raise ...
gateway.charge(order.total, order.customer)

# Good — the extracted name replaces the comment
validate(order)
charge_customer(order)
```

---

## CM-003 — Comments explain *why*, not *what*

The comment that earns its place carries what the code cannot: the reason a choice was made, a non-obvious constraint, a link to the spec/ticket/bug, a warning about a sharp edge. That information isn't in the syntax, so it can't be recovered by reading harder.

```go
// Good — none of this is visible in the code itself
// Stripe rounds half-to-even; we round half-up to match the invoice PDF (FIN-2231).
amount = roundHalfUp(amount)

// Retry only 429/503 — retrying a 400 just resends a request the server already rejected.
if isTransient(status) { return retry(req) }
```

Legitimate comments: rationale, trade-offs, links to external context, warnings/invariants, and the formal API doc on a *public* surface (see CM-004). Everything else is suspect.

---

## CM-004 — No redundant docstrings, banners, or dividers

A docstring earns its place only by adding what the signature can't. One that restates the name and parameters is noise with extra steps — and it drifts out of sync the first time the signature changes.

```python
# Bad — says nothing the signature doesn't
def get_user(user_id: int) -> User:
    """Get the user.

    Args:
        user_id: the user id
    Returns:
        the user
    """

# Good — either nothing (the signature is self-evident)...
def get_user(user_id: int) -> User:
    ...

# ...or a docstring that adds real information
def get_user(user_id: int) -> User:
    """Raises NotFound if the user was soft-deleted (deleted_at set)."""
```

Also out: **banner/divider comments** (`# ===== HELPERS =====`, `// ---- end of section ----`) and **section labels inside a function** — if a function needs internal section headers, it's doing too many things (`functions.md` FN-002); split it. Vertical spacing groups concepts without a comment (`formatting.md` FMT-002).

---

## CM-005 — No filler, no narration of the change, no decoration

The tells that mark text as machine-generated or thinking-out-loud, none of which belong in source:

- **Filler preambles** — `Note:`, `Important:`, `Here's how this works:`, `As you can see`, `Basically`. If the point matters, state it plainly as the comment; if it doesn't, cut it.
- **Narrating the edit** — `// Updated to handle the null case`, `# Changed from the old approach`, `// NEW:`, `// (added for the refactor)`. That history belongs in the commit message and `git log`, not the code — it's meaningless to the next reader and instantly stale.
- **Decoration** — emoji, ASCII art, and exclamation marks in comments. They read as generated, not written.
- **Restating the task** — a comment that parrots the prompt/ticket ("This function implements the user story for checkout") instead of saying something useful about the code.

```ts
// Bad
// 🚀 Here's the main function! Updated to also handle empty input.
// This implements the checkout feature as requested.
export function checkout(cart: Cart) { ... }

// Good — no comment; the name and types are the documentation
export function checkout(cart: Cart) { ... }
```

**The line for every comment:** would a competent reader who has the code in front of them be *better off* with this sentence than without it? If not, it's one of the above — delete it.
