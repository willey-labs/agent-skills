# Rule index — find a rule by the question you're asking

The rules are organized by **what kind of question you're asking**, not by language. Use this index to jump to the right reference; the rule codes (FN-*, NM-*, OD-*, FMT-*, CM-*, EH-*, DP-*, ST-*) live inside each file with worked examples.

**Functions** — size, argument count, side effects, command/query separation, exceptions vs error codes
→ `references/common/functions.md`

**Naming** — intention-revealing, no Hungarian, meaningful distinctions, pronounceable, searchable
→ `references/common/naming.md`

**Classes, objects, data structures** — getters vs behavior, Law of Demeter, hybrid classes, DTOs, no type-system escape hatch (`any`/`Any`/`interface{}`/`dynamic`/`mixed`, OD-006)
→ `references/common/objects-and-data.md`

**File layout, vertical spacing, declaration placement, team conventions**
→ `references/common/formatting.md`

**Comments & docstrings** — no narration, why-not-what, no redundant docstrings/banners, no filler or change-narration (review-only, no hook)
→ `references/common/comments.md`

**Try/catch, exception design, error translation at boundaries**
→ `references/common/error-handling.md`

**SOLID, KISS, DRY, dependency inversion, single responsibility**
→ `references/common/code-principles.md`

**Folder-as-module, no deep imports, Rule of Three, nesting legitimacy (nested peer vs sub-feature, ST-009), no junk-drawer files (universal)**
→ `references/common/structure.md`

**Folder structure for the specific framework (Next.js routes, NestJS modules, Laravel skeleton, etc.)**
→ `references/<framework>/structure.md`
