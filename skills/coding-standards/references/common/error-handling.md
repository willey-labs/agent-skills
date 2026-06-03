# Error Handling

Language-agnostic rules for separating the happy path from failure handling.

See also `functions.md` FN-010 (signal failure the *idiomatic* way for your language, not error codes ported from another).

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

## EH-002 — Translate failures at boundaries; never swallow

Two failure modes ruin trust in a system, regardless of language:

1. **Raw implementation failures leak out.** A `SqlException`, `JsonParseError`, or `SocketTimeoutException` thrown — or a `pgx.ErrNoRows` / `sqlx::Error::RowNotFound` returned — from deep in the stack tells the caller about the *implementation* of a failure, not the *meaning* of it. The caller now depends on storage choices, transport choices, and library versions to know what to handle.

2. **Failures are silently dropped** (`catch (e) {}`, `if err != nil { _ = err }`, `.unwrap_or_default()` on a real error). The failure happened but nobody knows. Bugs hide here forever.

**The rule:** at every boundary where a meaningful operation completes, translate raw failures into **domain failures** that describe what went wrong in terms the caller cares about.

The mechanism differs by language; the rule does not.

**Exception languages** (Java/C#/Python/JS/Ruby/PHP) — `try` the implementation work, `throw` a domain exception in `catch`:

```ts
async function withdraw(accountId, amount) {
  try {
    const account = await db.fetchAccount(accountId);   // can throw SqlException
    account.balance -= amount;
    await db.save(account);                             // can throw SqlException
  } catch (e) {
    throw new TransactionFailed({ cause: e });          // domain exception
  }
}
```

**Result languages** (Rust/Kotlin/Swift/Haskell/OCaml) — map the raw error type into a domain error type at the boundary, preserving the cause:

```rust
pub async fn withdraw(account_id: AccountId, amount: Money) -> Result<(), TransactionFailed> {
    let mut account = db::fetch_account(account_id)
        .await
        .map_err(TransactionFailed::from_db)?;   // raw SqlError → TransactionFailed
    account.balance -= amount;
    db::save(&account)
        .await
        .map_err(TransactionFailed::from_db)?;
    Ok(())
}
```

**Go** — wrap with `fmt.Errorf("...: %w", err)` or a custom error type so callers see a domain-named error but `errors.Is` / `errors.As` still find the cause:

```go
func Withdraw(ctx context.Context, accountID AccountID, amount Money) error {
    account, err := db.FetchAccount(ctx, accountID)
    if err != nil {
        return fmt.Errorf("withdraw: %w", ErrTransactionFailed)
    }
    account.Balance -= amount
    if err := db.Save(ctx, account); err != nil {
        return fmt.Errorf("withdraw: %w", ErrTransactionFailed)
    }
    return nil
}
```

In every case the caller handles `TransactionFailed` (or its language equivalent). If the persistence layer changes from SQL to a remote API tomorrow, the callers don't move.

**Never silently drop a failure.** If you genuinely need to ignore one (e.g. best-effort cleanup), log it at minimum and add a one-line comment saying why ignoring is correct here. `catch (e) {}`, `_ = err`, `let _ = result;` without an explicit reason are all the same bug — silent failure.

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

---

## EH-004 — Async failures are real failures

Asynchronous code — Promises, futures, async/await, channels, callbacks — does not get a pass on the rules above. The same boundary translation and same no-swallow discipline apply, but the *failure paths* are easier to hide. Two common bugs:

**1. The unawaited operation.** A function fires off async work without awaiting (or `.then`-ing) it. If that work fails, no caller handles the failure — and depending on the runtime, the process may crash with an "unhandled rejection" hours later.

```ts
// ❌ Bug — error from sendEmail is unobserved
function notifyAndContinue(user) {
  sendEmail(user)            // returns Promise; not awaited, not .catch()ed
  return { ok: true }
}

// ✅ Fix — either await it (and let the caller see the failure)
async function notifyAndContinue(user) {
  await sendEmail(user)
  return { ok: true }
}

// ✅ Or explicitly fire-and-forget with a documented catch
function notifyAndContinue(user) {
  sendEmail(user).catch(e => logger.warn({ err: e }, 'best-effort email failed'))
  return { ok: true }
}
```

The rule: every Promise/Future/Task either gets *awaited* by something, *returned* to a caller who will await it, or *explicitly* attached to a handler that documents the choice to ignore.

**2. Concurrent failures swallowed by parallel combinators.** `Promise.all(...)` rejects on the first failure but does not cancel the others — and `Promise.race(...)` resolves on the first settle but leaks the losers. Choose deliberately:

| You want | Use |
|---|---|
| All-or-nothing: one failure aborts the batch | `Promise.all([...])` — but be aware sibling work keeps running until its own completion |
| Best-effort: collect every outcome, including failures | `Promise.allSettled([...])` — returns the per-task result so the caller can decide |
| First-success: fastest non-failing wins | `Promise.any([...])` — rejects only if every task failed |
| First-settled (could be a rejection): use rarely | `Promise.race([...])` |

For other ecosystems the names differ — Rust's `tokio::try_join!` / `tokio::join!`, Kotlin's `awaitAll` / `supervisorScope`, Go's `errgroup.Group` — but the four shapes are the same. Pick the one whose failure semantics match what you actually want, and write a comment if it isn't obvious.

**3. Cleanup paths.** Open resources (files, connections, transactions, locks) must release whether the work succeeds or fails. Use the language's resource-scoping construct:

- JS/TS / Python — `try { ... } finally { release() }` or context managers (`with`, `using`).
- Java/Kotlin — try-with-resources.
- Rust — RAII via `Drop` (automatic for owned types; explicit guards for borrowed ones).
- Go — `defer release()` immediately after acquiring the resource.
- C# — `using` statement or `await using` for `IAsyncDisposable`.

The pattern across all languages: *acquire on one line, schedule release on the next*. Don't let cleanup live at the bottom of a function — when an early return or thrown exception jumps out, the cleanup is skipped.
