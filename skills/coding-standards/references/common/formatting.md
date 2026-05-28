# Formatting

Language-agnostic rules for how code is laid out on the page. These rules don't change runtime behavior — they change how fast a reader can navigate and how much trust the file builds.

---

## FMT-001 — The newspaper rule

A source file should read like a newspaper: the headline at the top, supporting paragraphs below, fine details at the bottom.

**The rule:** the highest-level function sits at the top of the file. Each function is defined **just below its first caller**, so reading the file flows naturally downward from intent → detail.

```
function generateReport() {        ← headline (high level)
  const data = fetchUserData();
  const report = buildReport(data);
  saveReport(report);
}

function fetchUserData()  { ... }  ← defined in call order
function buildReport(d)   { ... }
function saveReport(r)    { ... }

// Shared utilities at the bottom — grouped by conceptual affinity
function formatDate(d)    { ... }
function formatScore(s)   { ... }
```

**Two kinds of grouping:**
1. **Call order** — when one function calls another, the callee is defined right below. The reader sees a call, expects a definition, and finds it.
2. **Conceptual affinity** — functions that share a purpose (`formatDate` / `formatScore`) sit together even if neither calls the other. Same prefix → same neighborhood.

**Apply:** when a reader sees a function call, the definition should be close enough that no scrolling is required to find it. If the file forces scrolling, restructure.

---

## FMT-002 — Vertical spacing separates concepts; dense lines group them

Even well-written code is hard to read when it's a wall of text. Blank lines tell the reader *a new concept starts here*.

**The two halves of the rule:**

- **Blank lines between concepts.** Each blank line is a signal — "the next block is a different idea." Scan by gaps, then read into a block when you find the right gap.
- **Dense lines within a concept.** Related lines stay tight together. Spacing everywhere is just as bad as spacing nowhere — both flatten the visual hierarchy.

Inside one function, density should reveal three or so groups:

```
function publishOrder(input) {
  const order = parseOrderInput(input);          ← group 1: extraction
  const validated = validateOrder(order);

  const billed = applyTax(applyDiscount(validated));   ← group 2: business logic
  const charge = chargeCustomer(billed);

  notifyWarehouse(charge);                        ← group 3: side effects & result
  return charge.confirmationCode;
}
```

Three blocks, each with one clear purpose. The reader navigates by white space, not by reading every line.

**Indentation:** every scope level gets its own indent. This is the visual hierarchy that lets the reader see scope at a glance — not optional, not a style choice for nested blocks.

---

## FMT-003 — Declarations live close to where they are used

Every variable declared early is mental baggage the reader carries until it's finally used.

**Local variables:**

- Declare at the point of first use, **not** at the top of the function. If the variable is only used inside a loop or branch, declare it inside that scope.
- If first use is more than a few lines away from the declaration, move the declaration closer.

```
// Bad — reader carries `skippedLog` and `report` through the whole function
function processBatch(items) {
  const skippedLog = [];
  const report = createEmptyReport();
  // ...30 lines that don't touch either...
  if (someCondition) {
    skippedLog.push(item);
  }
  // ...more lines...
  return finalizeReport(report);
}

// Good — declarations meet usage
function processBatch(items) {
  // ...30 lines of work...
  if (someCondition) {
    const skippedLog = [];                       ← used immediately
    skippedLog.push(item);
  }
  // ...
  const report = createEmptyReport();            ← used right after
  return finalizeReport(report);
}
```

**Class properties** are the opposite: by design, class properties are shared across methods. Placing a property right above the one method that uses it only makes other readers (and other methods) search harder.

**The rule for properties:** group them in **one designated place** — the top of the class (most languages) or the bottom (some communities). Pick a convention and apply it everywhere in the file. Don't scatter them next to individual methods.

---

## FMT-004 — Team conventions for everything else

A pile of "style" decisions has no objectively correct answer:
- Braces on the same line, or the next?
- Tabs or spaces?
- Single quotes or double?
- Trailing commas, semicolons, line length?

**These are team decisions, not universal rules.** The job of formatting is to get out of the way of understanding. Once the team picks, the code base must be consistent — inconsistency is the actual smell, not the specific choice.

**Apply:**
- When editing an existing file, **match the file's existing style** — brace placement, quotes, indentation, line endings.
- When the project has a formatter (Prettier, gofmt, csharpier, php-cs-fixer, dotnet format), the formatter is the source of truth. Don't argue with it.
- When the file has no clear convention, follow the most recent commits in the area; if still ambiguous, follow the language's community default.
