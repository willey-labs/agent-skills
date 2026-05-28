# Functions

Language-agnostic rules for function design. Apply to methods, procedures, functions, and callables in any language.

---

## FN-001 — Functions must be small, then smaller

Long functions hide intent under noise. Reading a function should not feel like a mental workout.

**Target:** ≤ 20 lines of body (blanks/comments excluded). When you exceed it, extract until each piece tells its own story through its name.

**How to apply:**
- Wrap low-level detail clusters behind clear function names so the parent function reads as a sequence of intents.
- A block inside `if` / `else` / `while` / `for` should be **one line long** — typically a single function call. Inline logic inside a control block is a signal that the inner code wants to be its own function with a name that explains it.

**Why:** Extracting names gives the reader vocabulary. After the extraction you no longer need to explain the function — the names do it.

---

## FN-002 — A function does exactly one thing

A function doing multiple things has multiple reasons to change, multiple tests to write, and multiple ways to confuse the next reader.

**Two ways to know it's doing more than one thing:**
1. **Section test** — if you can label chunks ("initialization", "logic", "cleanup"), each chunk is a separate responsibility.
2. **Extraction test** — if you can extract another function with a name that is *not just a restatement* of its implementation, it was doing more than one thing. "uploadBasedOnSize" restates the body; "performMultipartUpload" names a distinct concept — extract the latter.

**How to apply:** keep extracting until the next extraction would just rename the body. That's the stopping point.

---

## FN-003 — One level of abstraction per function

Mixing high-level intent ("process the order") with low-level detail ("call `stripe.charges.create` with these headers") obscures the code's purpose.

**The rule:** a function should read as a top-down narrative, descending one layer of abstraction at a time. The CEO doesn't pack boxes. The order processor doesn't know Stripe's raw API.

**How to apply:** each function reads like a two-sentence paragraph at one level:
- *To process an order, we validate stock, calculate the bill, charge the customer, and notify the warehouse.*
- *To calculate the bill, we sum the items, apply discounts, and add tax.*

If you see an HTTP call sitting next to a domain concept like `applyLoyaltyDiscount`, the levels are mixed — push the HTTP call down a layer.

---

## FN-004 — Bury switch statements in factories

A `switch` (or `match`, or chained `if/else if`) by its nature does *n* things — one branch per case. That conflicts with FN-002.

**The smell:** the same switch on the same type appears in multiple functions (`calculatePay`, `calculateBenefits`, `scheduleShift`...). Adding a new case means hunting every copy.

**The fix:** polymorphism. Each type implements a common interface. The switch lives **once**, in a factory that returns the right object. After construction, no switch is needed — you call `obj.calculatePay()` and dispatch is automatic.

**How to apply:** if you see the same type dispatch in 2+ functions, extract a factory and let the returned object own its own behavior.

---

## FN-005 — Keep argument count low

Arguments carry mental weight. Each one is something the reader must remember, something to test, something to get in the wrong order.

| Count | Rating |
|---|---|
| 0 | Ideal — nothing to remember |
| 1 | Clear |
| 2 | Acceptable |
| 3 | Signal — group them into a named object |
| 4+ | Reject |

**How to apply:** when arguments pile up, they are telling you they want to be an object. Group the related ones and pass the *idea*, not the pieces. `createUser(name, email, age, role, plan)` becomes `createUser(userDetails)`.

---

## FN-006 — Single-argument functions serve one of three purposes

A function that takes one argument should be one of:
1. **Asking a question** — `isAdmin(user)` returns a boolean answer about its input.
2. **Transforming input** — `parseDate(string)` returns something new derived from the input.
3. **Handling an event** — `onUserSignedUp(user)` reacts to something that happened.

**Anti-patterns:**
- **Flag arguments** that select which branch runs inside the function. `render(true)` forces the function to do two different jobs. Passing `true` *as data* (`setVisible(true)`) is fine — the boolean is the value, not a switch.
- **Output arguments** that mutate their input instead of returning. Data flows in through arguments and out through return values. Mutating an input violates that expectation.

---

## FN-007 — Argument pairs and triads need care

Two-argument functions are not all equal:

- **Natural pairs** — coordinates `(x, y)`, ranges `(start, end)`, key/value — belong together. Keep them.
- **Unrelated pairs** — when two unrelated concepts share the signature, make one the owner: `user.addRole(role)` instead of `addRole(user, role)`.

**Triads are the danger zone.** Three arguments of similar type (`assertEquals(expected, actual, message)`) trap readers. Order is invisible at the call site. When you cannot avoid a triad:
- Use a rigid, natural ordering readers already know (`x, y, z`), or
- **Encode the order into the name** — `assertEqualsExpectedActual(...)`, `drawRectFromTopLeft(...)`. The name becomes its own documentation.

---

## FN-008 — No side effects beyond what the name promises

A function named `checkPassword` should *check* the password — nothing more. If it also reinitializes the session, it lies. Callers expect a check, get unexpected state changes, and bugs hide in the gap.

**How to spot:** ask "if a reader knew only the function name, would the body surprise them?" If yes, you have a hidden side effect.

**Common offenders:**
- Verifying state but also writing to it.
- Reading data but also caching/logging via a non-obvious channel.
- Setting an unrelated class property as a "convenience."

**The fix is not renaming** (`checkPasswordAndStartSession`) — that just acknowledges two jobs. Split the function so each part does one thing and the caller composes them.

---

## FN-009 — Command-Query Separation

A function either **does** something (command, mutates state) **or answers** something (query, returns information). Never both.

**The smell:** `if (setAttribute(name, value)) { ... }` — is the condition checking whether the update succeeded, or whether the attribute already existed? You can't tell without reading the implementation.

**The fix:** split.
- `attributeExists(name)` — query, returns the answer.
- `setAttribute(name, value)` — command, performs the action.

Now the call site reads like a conversation: *Does it exist? No. Then set it.* Commands change state; queries return answers. Keep them separate.

---

## FN-010 — Prefer exceptions over error codes

Error codes force every caller to check, branch, and propagate — turning straight-line logic into nested guards. They also typically live in a shared enum that couples the entire codebase.

**The contrast:**

```
// Error codes — algorithm disappears under guards
if (addUser(...) === Error.OK) {
  if (addProfile(...) === Error.OK) {
    if (addEmail(...) === Error.OK) {
      ...
    }
  }
}

// Exceptions — algorithm is visible, error handling is one block
try {
  addUser(...);
  addProfile(...);
  addEmail(...);
} catch (e) {
  ...
}
```

**Further:** extract the `try` body into its own function so normal processing and error processing aren't sitting side by side. The algorithm reads as an algorithm; the error handler reads as an error handler.

---

## FN-011 — DRY: every piece of knowledge has one authoritative source

Duplication is the root of subtle bugs. When the same logic appears in many places, updating it everywhere is hectic — and missing one leaves a silent bug.

**The principle:** every piece of knowledge must have a single, unambiguous, authoritative representation within a system.

**How to spot:**
- Two functions whose bodies are 80%+ identical with only a parameter swapped — they want to be one function with that parameter.
- A constant value (timeout, retry count, URL) appearing in multiple files — extract a single source.
- The same business rule expressed in two layers (database constraint + application validator + UI check) — pick one authoritative layer and derive the rest.

**Caveat:** *accidental* repetition that just happens to look the same is not duplication. Two unrelated rules that share a value today may diverge tomorrow. DRY is about shared *knowledge*, not shared *characters*.

---

## FN-012 — Clean code is rewritten, not written

Nobody writes the final form on the first try. First drafts are messy: nested loops, weak names, long argument lists, duplication. **That is fine** as long as tests cover the behavior.

**Process:** write it ugly first to get the logic working. Then refactor with confidence — split functions, rename, eliminate duplication — iteration by iteration until the code matches the rules above.

This rule is permission to draft. It is **not** permission to leave the draft.
