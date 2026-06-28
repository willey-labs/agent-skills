# Source → deliverable (SD)

You read a *source* — existing code, or a discussion — to understand something, then write a
*deliverable* — a document, a rule, a skill. The failure this set stops: pasting the source into
the deliverable. The source is what you learned from. It does not appear in the output.

Why it happens: the source is the most concrete material in front of you, so copying it is the
cheapest next move. Abstracting it into its effect is harder and feels riskier, so the default is
to echo. These rules force the abstraction.

---

## SD-001 — A document about code contains no code

Describe what the system *does* — its effect — in plain language a non-coder can read. No code
blocks, no function/class/file names, no line numbers, no framework role names. Treat the code as
something you read to learn the behaviour, then write as if the code were not yet written and the
infrastructure already existed.

Source:

```python
def reset_password(email):
    token = make_token()
    cache.set(token, email, ttl=3600)
    send_email(email, f"Reset link: /reset/{token}")
```

**Bad** — re-types the code in sentences:
> The `reset_password(email)` function calls `make_token()`, stores it in `cache` keyed by the
> token with a 3600-second TTL, then calls `send_email` with a link containing the token.

**Good** — states the effect:
> Requesting a password reset emails the person a link that works for one hour.

The bad version only makes sense to someone who has read the code. The good version makes sense to
the reader who hasn't.

## SD-002 — Don't inventory the code

No file lists, no "the `X` module contains…", no walking the reader through the call graph. Name
real infrastructure as a capability ("the queue", "the cache", "the audit log"), never as the
codebase's class, method, file, or framework role.

## SD-003 — A rule states the principle, not the case that prompted it

When a discussion produces a rule, write the general principle. The specific example you just
discussed is scaffolding — it got you to the understanding; it stays out of the rule.

Discussion: *"The signup handler wrote the user's raw password into the debug log."*

**Bad** — bakes in the one case:
> The signup handler must not write the raw password to the debug log.

That rule covers one handler and one field. It's a retelling of the bug, not a rule.

**Good** — the principle, example dropped:
> Never log credentials or secrets.

## SD-004 — Rewrite any sentence that needs the source to parse

After drafting, reread as someone who never saw the code or the discussion. Any sentence that only
makes sense if you'd read the source is a leak — rewrite it as an effect.

## SD-005 — Examples are freshly invented, never lifted from the source

Applies to every document, not just rules. An example you include must be a minimal illustration
you invent for the page. Never paste the specific case — the names, paths, snippet, or scenario —
from the discussion or the code that prompted the document.

The conversation's example is the most salient thing in front of you, so it's the cheapest to
reuse, and that's the trap: reusing it means you echoed instead of abstracted, and it chains the
document to a context the reader never saw. Strip the source to its principle, then write a fresh
example that shows only that principle. Struggling to invent one is a signal you haven't abstracted
the principle yet — do that first.

---

## SD-EXC — The one place code belongs

An **external service the system depends on**: include the ready-to-use call — its function and
endpoint — because the reader needs it to use the system. That's a contract, not internal code.
Everything above governs the system's *own* internals; this exception is only for the outside
service.

This reference itself shows code samples — that's allowed because its subject *is* the rule, and
the samples are the bad/good contrast that teaches it. A teaching reference is a different genre
from the deliverables the rule governs. Don't use this as a loophole: a README about your code is a
deliverable (no code, SD-001), not a teaching reference.
