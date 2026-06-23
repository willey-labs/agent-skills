# Functions

Language-agnostic rules for function design. Apply to methods, procedures, functions, and callables in any language.

---

## FN-001 — Functions must be small, then smaller

Long functions hide intent under noise. Reading a function should not feel like a mental workout.

**Target:** small enough that one screen of the editor reveals the whole function and the reader can answer *what does this do?* without scrolling. In most languages that is ~20 lines of body (blanks and comments excluded); in higher-ceremony languages with longer property/constructor scaffolding (C#, Java, Kotlin) it can be ~30. The number is not the rule — *fits on a screen* is the rule.

**How to apply:**
- Wrap low-level detail clusters behind clear function names so the parent function reads as a sequence of intents.
- A block inside `if` / `else` / `while` / `for` should be **one line long** — typically a single function call. Inline logic inside a control block is a signal that the inner code wants to be its own function with a name that explains it.

**Why:** Extracting names gives the reader vocabulary. After the extraction you no longer need to explain the function — the names do it.

**When NOT to extract:**
- The function is already a linear sequence at one level of abstraction (see FN-003) — extracting steps that are only called from here adds indirection without adding meaning.
- The "long" function is mostly declarative (a table of cases, a schema definition, a `match` arm list). The data is the point; extraction just splits one table into two halves.
- Splitting would force you to invent a name that is *just a restatement of the body* (see the FN-002 extraction test). If you can't name the extracted piece distinctly, leave it inline.

---

## FN-002 — A function does exactly one thing

A function doing multiple things has multiple reasons to change, multiple tests to write, and multiple ways to confuse the next reader.

**Two ways to know it's doing more than one thing:**
1. **Section test** — if you can label chunks ("initialization", "logic", "cleanup"), each chunk is a separate responsibility.
2. **Extraction test** — if you can extract another function with a name that is *not just a restatement* of its implementation, it was doing more than one thing. "uploadBasedOnSize" restates the body; "performMultipartUpload" names a distinct concept — extract the latter.

**How to apply:** keep extracting until the next extraction would just rename the body. That's the stopping point.

---

## FN-003 — One level of abstraction per function

Mixing high-level intent ("process the order") with low-level detail ("call the payment API with these headers") obscures the code's purpose.

**The rule:** a function should read as a top-down narrative, descending one layer of abstraction at a time. The CEO doesn't pack boxes. The order processor doesn't know the payment provider's raw API.

**How to apply:** each function reads like a two-sentence paragraph at one level:
- *To process an order, we validate stock, calculate the bill, charge the customer, and notify the warehouse.*
- *To calculate the bill, we sum the items, apply discounts, and add tax.*

If you see an HTTP call sitting next to a domain concept like `applyDiscount`, the levels are mixed — push the HTTP call down a layer.

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
| 3 | Signal — usually wants grouping into a named object |
| 4+ | Almost always wrong — group them (rare exception: a genuinely irreducible natural tuple like matrix coordinates — see the enforcement note below) |

**How to apply:** when arguments pile up, they are telling you they want to be an object. Group the related ones and pass the *idea*, not the pieces. `createUser(name, email, age, role, plan)` becomes `createUser(userDetails)`.

**Languages with named arguments** (Python, Swift, Kotlin, Dart, C#) soften this rule a little: `placeOrder(customerId=..., items=..., discount=..., shippingAddress=...)` reads fine at the call site because each argument is labeled. The mental-load problem (which arg is which) goes away. Even so, when you reach 5+ named arguments the parameter list is usually a missing object — extract a `PlaceOrderRequest` and the function signature describes the *operation* (`placeOrder(request)`), not its data layout.

**Languages without named arguments** (JavaScript/TypeScript, Go, Java, PHP, Rust without builder) hit the rule harder — a positional 4-tuple at the call site (`createUser(a, b, c, d)`) is genuinely unreadable. Group earlier. So the enforced line is **4+ for positional languages (JS/TS, Go, Java, PHP) and 5+ for the named-argument ones (Python, C#, Kotlin, Swift, Dart)**.

**Carve-outs — shapes that are not call sites.** The threshold counts *arguments a caller must pass*. Some 4+/5+ parameter lists aren't that, and are exempt (the write-time hooks encode these, and review treats them the same):

- **Constructors that the framework calls, not you** — a dependency-injected constructor (TypeScript/NestJS parameter properties `constructor(private a: A, …)`, PHP promoted `__construct`, Spring/Java and C# constructors, Go `New…` wiring functions). The container is the caller; the parameters *are* the object's fields. Group them only when the wiring genuinely hurts, not because of the count.
- **Record / data-class declarations** (`record OrderResponse(…)`, Kotlin `data class`, the DTO carriers the framework structure refs mandate). The components are fields, not arguments.
- **Framework parameter bindings** — FastAPI `Depends()`/`Query()`/… parameters, the Express `(err, req, res, next)` error-middleware shape, pytest fixture parameters. Each parameter is a framework binding, not an argument you chose.

These are exemptions by *shape*, not a license to raise the count: an ordinary function or method with 4+/5+ real arguments still groups them into an object.

**Enforcement note — the "natural tuple" is not a hook exemption.** The write-time hook enforces the 4+/5+ line literally; a coordinate tuple `(x, y, z, w)` blocks too. The only carve-outs the hook honors are the *shape* ones above (DI constructors, records, framework bindings). If a tuple is genuinely irreducible, that is a **review-time `accepted` with a reason** (per the review/fix model), never a silent write-time pass — the call at review is still binary: it's `accepted` (with the reason naming why) or it's a violation.

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

## FN-010 — Make failure handling invisible to the algorithm

Keeping failure handling out of the algorithm's visible body is EH-001's job (see `error-handling.md`,
which has the before/after). This rule is the other half: *how* a function signals failure once it's
separated out. Use **whichever idiomatic failure mechanism your language gives you** — not error codes
ported in from another language:

| Language family | Idiomatic mechanism | What the algorithm looks like |
|---|---|---|
| Java, C#, Python, JavaScript, Ruby, PHP | Exceptions thrown out, caught at a boundary | `try { addUser(...); addProfile(...); addEmail(...); } catch (e) { ... }` |
| Rust, Kotlin, Swift, Scala, Haskell | `Result` / `Either` / `Try` returns combined with `?` / `map` / `flatMap` / for-comprehension | `let user = add_user(...)?; let profile = add_profile(...)?; add_email(...)?;` |
| Go | `(T, error)` returns + the explicit `if err != nil` chain, OR error wrapping with `errors.Join` / `fmt.Errorf("...: %w", err)` to translate at boundaries | `user, err := addUser(...); if err != nil { return fmt.Errorf("signup: %w", err) }` |
| OCaml, F# | `result` type with pattern matching or computation expressions | similar to Rust |

The key word in each row is **idiomatic**. Exceptions in Rust, `Result` in Java, or error codes anywhere — these go against the grain and force every reader to relearn how the language signals failure.

**The shared smell across all languages:** an `if (err)` guard sitting on every business step, scattering the failure-handling logic across the work. The fix differs by language; the principle (keep failure handling out of the algorithm's visible body) does not.

**Further:** extract the `try` body (or the chain of `?` operators, or the `if err != nil` block) into its own function so normal processing and error processing aren't sitting side by side. The algorithm reads as an algorithm; the error handler reads as an error handler.

See `error-handling.md` for the boundary translation rule (EH-002) — these two together are how failure is kept clean across languages.

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
