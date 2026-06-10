# Naming

Language-agnostic rules for naming variables, functions, classes, files, and any other identifier the reader will encounter.

A name is read hundreds or thousands of times more often than it is written. The cost of a bad name is paid by every future reader of the codebase. The rules below trade a few extra characters at write time for fast, unambiguous reads forever after.

---

## NM-001 — Names must reveal intent

A good name answers three questions without a comment: *why does this exist, what does it do, how is it used*.

**The smell:** a single-letter variable (`d`), an opaque abbreviation (`fltUsrLst`), or a generic word (`data`, `info`, `temp`) that forces the reader to chase the implementation to learn the meaning.

```
// Bad — reader has to trace `d` through the codebase
const d = computeElapsedDays(start, end);

// Good — the name answers "why" (only the variable changed; the function is the same)
const elapsedTimeInDays = computeElapsedDays(start, end);
```

```
// Bad
function filter(users) {
  return users.filter(u => u.s === 1);
}

// Good
function filterActiveUsers(users) {
  return users.filter(user => user.status === Status.Active);
}
```

**Apply:** if you find yourself writing a comment to explain a name, the name has failed — rename instead. If the comment would have read *"the elapsed time in days"*, the name should read `elapsedTimeInDays`.

**Exception:** loop counters `i, j, k` in a short loop scope and obvious short-lived locals (e.g. `e` for the parameter of a one-line lambda) are fine — the scope is small enough that the meaning is immediately visible.

---

## NM-002 — No disinformation

A name lies when it promises something it doesn't deliver. The two main forms:

**Wrong noun for the structure.** Calling a `Map` "accountList" is disinformation — *list* has a specific meaning to programmers (indexed sequence). The reader writes `accountList[0]` and gets the wrong thing. If it's a map, call it `accountsByEmail` or `accountIndex`.

**Names that differ by one character or look identical.**
- `getActiveUsers` vs `getActivatedUsers` — one word apart; auto-complete picks the wrong one half the time.
- Lowercase `l` and number `1`. Uppercase `O` and number `0`. Visually indistinguishable in many fonts.

**Apply:**
- The noun in the name must match the actual structure (`List`, `Set`, `Map`, `Queue`, `Iterator` mean what they say).
- If two identifiers in the same scope differ by only one character, rename one to be clearly distinct.
- Never name a variable `l`, `I`, `O`, or anything that visually collides with a digit.

---

## NM-003 — Meaningful distinctions only

If two things have different names, they must do genuinely different things. If you can't tell them apart from their names, neither can your reader.

**The smells:**

- **Number suffixes.** `data1`, `data2`, `data3` say nothing about how they differ. Replace with names that describe the actual roles: `rawData`, `sanitizedData`, `enrichedData`.
- **Noise words.** `Manager`, `Handler`, `Data`, `Info`, `Processor`, `Helper` are placeholders developers reach for when they don't have a better idea. `UserManager` vs `UserHandler` — which does which? Pick role-specific names: `UserAuthenticator`, `UserDirectory`, `UserNotificationDispatcher`.
- **Generic parameter names.** `function f(a, b, c)` — every parameter looks identical. Rename to describe their roles: `function transfer(fromAccount, toAccount, amount)`.

**Test:** show the names to a teammate without showing the code. If they can't predict the difference, the names are not making meaningful distinctions.

---

## NM-004 — Names must be pronounceable

If you can't say a name aloud, you can't discuss it in a code review or onboard a new hire who needs to ask about it. Programming is a social activity — names belong in human conversation.

```
// Bad — can't say it out loud
class DtaRcrd102 { ... }
const genymdhms = currentTimestamp();
const modymdhms = lastModifiedTimestamp();

// Good — sounds like English
class Customer { ... }
const generationTimestamp = currentTimestamp();
const modificationTimestamp = lastModifiedTimestamp();
```

**Apply:** if a name would survive being spoken in a meeting (*"Customer record one-oh-two…"* vs *"Data record one-oh-two"*), it's pronounceable. Acronym chains and consonant clusters fail this test.

**Acronyms that are themselves pronounceable** (HTTP, JSON, URL, SQL, API) are fine. The rule is about pronouncing the *name*, not banning acronyms.

---

## NM-005 — Name length must match scope

Wide-scope identifiers (module-level constants, exported functions, public classes) are read in many places far from their declaration. They need full descriptive names so each call site stands on its own.

Narrow-scope identifiers (loop counters, parameters of a tiny lambda) are read right next to where they're declared. A short name is fine — sometimes preferable, because length without purpose is just noise.

| Scope | Acceptable names |
|---|---|
| One-line lambda / 3-line block | `i`, `e`, `it`, `x` |
| Loop body | `i, j, k` for indices; `item` for the element |
| Short function (≤ 10 lines) local | `count`, `result`, `error` |
| Long function / method body | full descriptive names |
| Module / package / public API | full, searchable, unambiguous names |

**Searchability is the other half of this rule.** Constants like `7` and `5` are impossible to find in a codebase — they collide with file names, version numbers, and unrelated literals. Single-letter variable `e` is the worst — most common letter in English, useless to grep. The fix is the same: give them descriptive names so a search for them returns only relevant matches.

```
// Bad — what do 24 and 7 mean?
const totalHours = days * 24 * 7;

// Good — every value is named and searchable
const HOURS_PER_DAY = 24;
const DAYS_PER_WEEK = 7;
const HOURS_PER_WEEK = HOURS_PER_DAY * DAYS_PER_WEEK;
const totalHours = days * HOURS_PER_WEEK;
```

---

## NM-006 — No type-encoding in names (no Hungarian notation)

Encoding the type into the name (`strName`, `bIsActive`, `iCount`, `oUser`, `aList`) made sense in the 1990s when editors couldn't show you the type. They can now. The compiler catches type errors. The IDE shows the type on hover.

Encoding the type means writing the type twice — once where the compiler sees it, once in the name — and both can drift apart when refactoring. Strip the prefix; let the name describe the *intent*, not the *storage*.

```
// Bad
const strName = "Alice";
const bIsActive = true;
const iCount = 0;
const aUsers = [];

// Good
const name = "Alice";
const isActive = true;
const count = 0;
const users = [];
```

**Boolean naming convention** — booleans read better with a question prefix: `isActive`, `hasPermission`, `canEdit`, `shouldRetry`. That's a semantic prefix (asks a question), not a type prefix.

---

## NM-007 — No mental mapping

Don't make the reader remember what your abbreviations stand for. Every cryptic name adds an entry to the reader's mental lookup table, distracting from the actual logic.

```
// Bad — what are t, tx?
for (const t of transactions) {
  if (validate(t)) {
    process(t.tx);
  }
}

// Good — no translation required
for (const transaction of transactions) {
  if (isValid(transaction)) {
    process(transaction.id);
  }
}
```

**Apply:**
- Spell things out. `manager` over `mgr`. `controller` over `ctrl`. `transaction` over `tx`. The IDE will auto-complete; the readers will thank you.
- Two-letter math notation (`p, t, q` for "price, tax, quantity") is mental mapping. The formula is no shorter once you spell it out — `price + tax * quantity` reads identically to `p + t * q` — but only the spelled version is self-documenting.
- Common, universal abbreviations (`url`, `id`, `db`, `http`) are fine because every reader already has the mapping. The line is whether the abbreviation is universal in the field, not whether it's universal in your team.

---

## NM-008 — One word per concept

Pick one word for one abstract concept and stay with it. The smell is using `fetch`, `retrieve`, `get`, `load`, `read`, and `find` interchangeably across the codebase for what is *supposed to be* the same operation. The reader can't tell whether the variation is meaningful or arbitrary, and they reach for the wrong one when introducing a new method.

```ts
// Bad — same idea, three names
class UserService    { getUser(id) { ... } }
class OrderService   { fetchOrder(id) { ... } }
class ProductService { retrieveProduct(id) { ... } }

// Good — one verb for "load by ID"
class UserService    { findById(id) { ... } }
class OrderService   { findById(id) { ... } }
class ProductService { findById(id) { ... } }
```

**Apply:** the team picks a short verb table — *one word per concept* — and the whole codebase uses it. Typical choices:

| Concept | Pick one |
|---|---|
| Load by ID, may return null | `find` (returns `T \| null` / `Option<T>`) |
| Load by ID, must exist (throw if missing) | `get` (or `getOrThrow`) |
| List with filters / pagination | `list` or `query` |
| Persist a new entity | `create` |
| Persist an update | `update` or `save` (pick one) |
| Remove | `delete` (not `remove`, not `destroy` — pick one) |

**The corollary — one concept per word.** Don't reuse the same verb for genuinely different operations. If `add` means "append to a collection" everywhere, it must not silently also mean "create in the database" in one feature. Different operations get different verbs.

---

## NM-009 — Use solution-domain names *or* problem-domain names, deliberately

A name lives on a spectrum:

- **Problem-domain names** describe what the *business* sees: `Order`, `Customer`, `Invoice`, `Prescription`, `Appointment`.
- **Solution-domain names** describe what *programmers* see: `Visitor`, `Strategy`, `Observer`, `Repository`, `Adapter`, `Decorator`.

Both are legitimate when used *where they belong*.

**Prefer problem-domain names for the things the product actually has** — entities, use cases, capability folders. A folder named `appointments/` is more useful than one named `entities/`.

**Use solution-domain names only when you are genuinely using that pattern.** Calling a thing `OrderObserver` only makes sense if it actually implements the Observer pattern and a reader who knows the pattern will recognize the role from the name. A class named `OrderManager` claims a pattern (Manager) that doesn't exist — that's not a solution-domain name, that's a noise word (see NM-003).

**Apply:** when naming a new class or module, ask *whose vocabulary is this in?* If it's something a business analyst would recognize, use that word. If it's a pattern a programmer would recognize, use the pattern's name — *and ensure the class genuinely implements that pattern*.
