# Comments

Language-agnostic rules for comments and docstrings.

**The default is none.** Write the code so it needs no sentence, and write no sentence. A file with zero comments is the normal, correct outcome — not an omission to fill in. A comment is the one part of a file the compiler never checks, so it rots silently; the only one that earns its upkeep carries what the code cannot say at all (CM-003). Everything else is noise the reader has to wade through, and it buries the rare comment that matters.

Code that seems to need explaining is usually code that needs a better name or a smaller function. Fix that instead — the fix is permanent, the comment is upkeep forever.

This is where machine-generated code betrays itself: narrating every line, restating every signature, sprinkling `Note:` / `Important:` preambles, and leaving the conversation that produced the code sitting in the file. Clean code reads like a person wrote it on purpose.

**Enforcement** comes in three layers, because prose can't be regex'd and self-review can't be trusted:

1. **Write time, mechanical** — `hooks/advise-comment-slop.py` flags decoration, edit narration, filler preambles, reader address, first-person deliberation and untracked `TODO` as an **advisory** (exit 0 + stderr; it never blocks, because a legitimate rationale comment may contain any word).
2. **Turn end, judged** — `hooks/judge-comments.py` sends the comments the turn added to a **separate model call** with these rules, and holds the turn open until a delete or shorten verdict is applied. The second reader is the point: the pass that just wrote a paragraph of self-justification is the worst judge of whether it earns its place. Deleting or trimming a comment can't change behaviour, so the fix needs no approval. A finding that is genuinely wrong may be kept, with the reason stated in the reply.
3. **Review** — Worker 2 owns the full prose judgement (is this narration, does it explain *what* instead of *why*, does the docstring add anything).

Advisory, judge verdict or review finding, every one is a must-fix violation — there is no soft tier. (FMT-005 owns disabled code; CM-* owns prose.)

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

---

## CM-006 — No conversation in the source

A source file is not a message to a reader and not a transcript of how the code came to be. The decision that survived is in the code; the deliberation that produced it belongs nowhere. Out:

- **Addressing a person** — `// as requested`, `// let me know if you'd rather…`, `// feel free to change this`, `// as we discussed`, `// hope this helps`. There is no "you"; there is the next reader, who wants the code, not the correspondence.
- **First-person deliberation** — `// I went with a map here, seemed cleaner`, `// I've kept the old branch just in case`. Thinking out loud is not documentation.
- **Weighing alternatives inline** — `// we could also batch these`, `// we should probably revisit this`. A rejected option is only worth a line when it reads as a *constraint*, not a musing: `// the bulk endpoint drops ordering, so we send one per row`.
- **Questions left in place** — `// not sure if this handles an empty list?`, `// does this need a lock?`. An open question in shipped code is a bug the author decided not to look at. Answer it, or make the uncertainty explicit as a failure the code handles.
- **Untracked `TODO` / `FIXME`** — either do it now, or record it where work is actually tracked and cite that reference in the comment. A bare `// TODO: clean this up later` is a wish; nobody reads it again.

```rust
// Bad — the chat, pasted into the file
// I switched this to a lookup table as you suggested — let me know if the loop
// reads better. Not sure whether the empty case can even happen here?
// TODO: maybe tidy up later
fn tariff_for(code: &str) -> Tariff { ... }

// Good
fn tariff_for(code: &str) -> Tariff { ... }
```

The register is the giveaway: if the sentence would fit in a chat message or a pull-request comment, that is where it belongs. Put it there, and leave the file clean.

---

**The line for every comment:** would a competent reader who has the code in front of them be *better off* with this sentence than without it? If not, it's one of the above — delete it.
