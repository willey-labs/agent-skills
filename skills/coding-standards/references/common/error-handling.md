# Error Handling

Language-agnostic rules for separating the happy path from failure handling.

See also `functions.md` FN-010 (prefer exceptions over error codes).

---

## EH-001 — Keep algorithm and error handling fully independent

Mixing logic with error checks at every step forces the reader to hold two stories at once: *what happens when it works* and *what happens when it doesn't*. Every check adds nesting; every nesting pushes the real work further from view. Eventually the algorithm disappears.

**The contrast:**

```
// Error codes everywhere — the algorithm is buried
function broadcastMessage(input) {
  const session = verifySession(input.token);
  if (session === Error.INVALID) {
    return { ok: false, code: Error.INVALID };
  }
  const channel = resolveChannel(input.channelId);
  if (channel === Error.NOT_FOUND) {
    return { ok: false, code: Error.NOT_FOUND };
  }
  const moderated = moderateContent(input.content);
  if (moderated === Error.BLOCKED) {
    return { ok: false, code: Error.BLOCKED };
  }
  return broadcastToMembers(channel, moderated);
}

// Exceptions — algorithm reads as four steps
function broadcastMessage(input) {
  const session   = verifySession(input.token);
  const channel   = resolveChannel(input.channelId);
  const moderated = moderateContent(input.content);
  return broadcastToMembers(channel, moderated);
}
// Error handling lives elsewhere — one place, one concern.
```

**The principle:** the algorithm doesn't know about error handling, and the error handling doesn't know about the algorithm. Either one can be read without the other interrupting.

**How to apply:** if the function body has more `if (err)` branches than business steps, the algorithm is buried. Switch to exceptions, or extract the error-checking pattern into a helper so the visible function is just the steps.

---

## EH-002 — Translate exceptions at boundaries; never swallow

Two failure modes ruin trust in a system:

1. **Raw implementation exceptions leak out.** A `SqlException`, `JsonParseError`, or `SocketTimeoutException` thrown from deep in the stack tells the caller about the *implementation* of a failure, not the *meaning* of it. The caller now depends on storage choices, transport choices, and library versions to know what to handle.

2. **Exceptions are silently caught and discarded** (`catch (e) {}` or `catch { /* ignore */ }`). The failure happened but nobody knows. Bugs hide here forever.

**The rule:** at every boundary where a meaningful operation completes, translate raw exceptions into **domain exceptions** that describe the failure in terms the caller cares about.

```
async function withdraw(account, amount) {
  try {
    const account = await db.fetchAccount(account.id);   // can throw SqlException
    account.balance -= amount;
    await db.save(account);                              // can throw SqlException
  } catch (e) {
    throw new TransactionFailed({ cause: e });           // domain exception
  }
}
```

Callers handle `TransactionFailed`. If the persistence layer changes from SQL to a remote API tomorrow, the callers don't move.

**Never empty-catch.** If you genuinely need to ignore an exception (e.g. best-effort cleanup), log it at minimum and add a one-line comment saying why ignoring is correct here.

---

## EH-003 — Define the try/catch contract before writing the logic

Most code is written body-first, error-handling-later. The result: error handling gets bolted on as an afterthought, with no clear contract about what the function promises to handle vs propagate.

**Reverse the order.** When you expect the body to throw, write the `try / catch / finally` skeleton **first**:

```
function withdraw(account, amount) {
  try {
    // logic goes here later
  } catch (e) {
    throw new TransactionFailed({ cause: e });
  }
}
```

Then write a test that asserts the failure mode: *if anything goes wrong inside withdraw, it should throw `TransactionFailed`*. The test will fail because the body is empty. The `catch` translates whatever gets thrown into the domain exception. Now write the body inside the `try` until the test passes.

**The contract is now explicit:** the function promises to throw `TransactionFailed` on failure. Every caller knows what to handle. Whatever you add inside the `try` later stays inside that contract — no new exception types leak out unless you choose to add them.

**Two reasons this matters:**
- Without a contract, callers don't know which exceptions to handle, so they handle none (or all). Both are wrong.
- With a contract, you can refactor the body freely — switch libraries, change algorithms — without breaking the failure interface that callers depend on.

**Each `try` block wraps one coherent operation with one clear failure mode.** Don't pile unrelated operations into one giant try; you'll lose the ability to distinguish what failed.
