# Next.js — Architecture

The chosen pattern for Next.js (App Router) projects: **Screaming Architecture + Mandatory Nesting** — top-level folders inside `src/` are business capabilities; every use case has the same internal skeleton; nothing global unless three places need it.

---

## The philosophy in one sentence

> Top-level folders scream the business. Inside each use case, files live in fixed technical subfolders. Nothing global unless three places need it.

---

## Mandatory shape

```
src/
  app/                              ← 🔧 Next.js router (THIN — no business logic)
    (patient)/
      dashboard/page.tsx
      appointments/
        page.tsx
        book/page.tsx
        [id]/page.tsx
    (doctor)/
      schedule/page.tsx
    (auth)/
      sign-in/page.tsx
    api/
      webhooks/
        stripe/route.ts
    layout.tsx
    page.tsx

  appointments/                     ← 📅 BUSINESS CAPABILITY (noun)
    book-appointment/               ←    🎯 use case (verb phrase)
      components/                   ←    ALL React components
      hooks/                        ←    ALL hooks
      lib/                          ←    ALL pure business logic
      api/                          ←    ALL server actions / fetches
      schemas/                      ←    ALL request/input validation schemas
      types.ts                      ←    use-case types
      constants.ts                  ←    when present
      index.ts                      ←    🚪 public API (REQUIRED)

    reschedule-appointment/
      components/
      lib/
      api/
      types.ts
      index.ts

    appointment.types.ts            ←    capability-scoped types
    appointment.constants.ts
    index.ts                        ←    🚪 capability public API

  prescriptions/                    ← 💊 BUSINESS CAPABILITY
    issue-prescription/
    refill-prescription/
    revoke-prescription/
    prescription.types.ts
    index.ts

  shared/                           ← 🧰 CROSS-CUTTING (3+ capabilities only)
    ui/                             ←    design system primitives
    lib/                            ←    infrastructure (named files only)
    hooks/                          ←    genuinely shared hooks
    config/
      env.ts
    types/
      global.ts                     ←    only truly app-wide types
```

---

## NXT-001 — Top-level folders must scream the business

| Allowed at the top of `src/` | Forbidden |
|---|---|
| ✅ Business capability folders (`appointments/`, `prescriptions/`) | ❌ `components/`, `hooks/`, `lib/`, `utils/`, `services/`, `models/` |
| ✅ `app/` (Next.js router) | ❌ Generic `types/`, `constants/`, `helpers/` |
| ✅ `shared/` | ❌ Anything that doesn't describe the product |

**Test:** open `src/` cold. Can you describe the product in 30 seconds from folder names alone? If no, the architecture is wrong.

---

## NXT-002 — `app/` is thin

The Next.js router (`app/` or `pages/`) handles routing and composition only. **No business logic.**

```tsx
// ✅ Good — app/ composes a use case
// app/(patient)/appointments/book/page.tsx
import { BookAppointmentForm } from '@/appointments'
export default function Page() {
  return <BookAppointmentForm />
}

// ❌ Bad — business logic inside the route
export default async function Page() {
  const slots = await db.query(...)            // DON'T
  const filtered = applyInsuranceRules(slots)  // DON'T
  return <form>...</form>
}
```

Use route groups `(group)/` and private folders `_internal/` from Next.js's official conventions when colocating page-only assets.

---

## NXT-003 — Use cases are verb phrases

Inside a capability, subfolders are **verb phrases**:

| Capability | Use cases |
|---|---|
| `appointments/` | `book-appointment/`, `reschedule-appointment/`, `cancel-appointment/` |
| `prescriptions/` | `issue-prescription/`, `refill-prescription/`, `revoke-prescription/` |
| `billing/` | `generate-invoice/`, `process-payment/`, `issue-refund/` |
| `identity/` | `register-patient/`, `sign-in/`, `reset-password/` |

**Test:** read the folder names aloud as a product spec. If they sound like requirements, you're right. If they sound like a technical inventory (`api/`, `forms/`, `data/`), you're wrong.

---

## NXT-004 — Every use case follows the mandatory shape

Same skeleton, every time. Add a folder when you write its first file — never before, but the slot is reserved:

```
<use-case>/
  components/      ← All React components live here
  hooks/           ← All hooks live here
  lib/             ← All pure business logic lives here
  api/             ← All server actions / fetches live here
  schemas/         ← All validation schemas live here
  types.ts         ← TypeScript types (file, not folder)
  constants.ts     ← when present
  index.ts         ← REQUIRED public API
```

**Forbidden:**
- ❌ A `.tsx` component file at the use-case root — must be inside `components/`.
- ❌ A `use-*.ts` hook at the use-case root — must be inside `hooks/`.
- ❌ Business logic at the use-case root — must be inside `lib/`.
- ❌ Empty folders (only create when you write the first file).
- ❌ `utils.ts` or `helpers.ts` anywhere — name files by what they do.

**Why mandatory:** when a use case grows from 3 to 15 files, you don't refactor — you add files into folders that already exist. Same shape everywhere = predictable navigation.

---

## NXT-005 — `shared/` requires three users

`shared/` is for code used by **3+ capabilities**. Code used by one or two capabilities lives in those capabilities, not in `shared/`.

| Allowed in `shared/` | Forbidden |
|---|---|
| ✅ `shared/ui/` — design system primitives (`Button`, `Input`, `Dialog`) | ❌ `shared/types.ts` mega-file |
| ✅ `shared/lib/` with **named** files (`date.ts`, `currency.ts`, `crypto.ts`) | ❌ `shared/utils.ts`, `shared/helpers.ts` |
| ✅ `shared/hooks/` — cross-cutting hooks (`use-debounce`, `use-media-query`) | ❌ Anything feature-specific |
| ✅ `shared/config/env.ts` | ❌ A feature-coupled hook with a generic name |

**Promotion process (Rule of Three):**

1. **First use** → inside the use case.
2. **Second use in the same capability** → promote to capability root (e.g. `appointment.types.ts`).
3. **Third use across capabilities** → promote to `shared/`.

**Never start in `shared/`.** Earn the promotion.

---

## NXT-006 — Dependency rules

```
app/                  → can import from any capability + shared
  ↓
capabilities          → can import from shared
                      → can import from OTHER capabilities ONLY via their index.ts
  ↓
shared/               → can import only from other shared/
```

```ts
// ✅ Allowed
import { Appointment } from '@/appointments'                  // via public API
import { formatCurrency } from '@/shared/lib/currency'

// ❌ Forbidden — deep import past the index.ts
import { confirmTimeSlot } from '@/appointments/book-appointment/lib/confirm-time-slot'

// ❌ Forbidden — capability importing from another capability internals
import { Prescription } from '@/prescriptions/issue-prescription/types'
```

**Enforce with ESLint's `import/no-restricted-paths`.**

---

## NXT-007 — Three type scopes

Types live at the narrowest scope that actually needs them. Promote upward only when proven.

```
src/
  appointments/                       ← capability
    book-appointment/
      types.ts                        ← ① use-case-level (private)
    appointment.types.ts              ← ② capability-level (shared across use cases)

  shared/types/
    global.ts                         ← ③ app-level (shared across capabilities)
```

| Level | Goes here | Example |
|---|---|---|
| ① Use-case | `<use-case>/types.ts` | `BookingStep`, `BookingFormState` |
| ② Capability | `<capability>.types.ts` | `Appointment`, `AppointmentStatus`, `AppointmentId` |
| ③ App | `shared/types/global.ts` | `UserId`, `Pagination`, `ApiResult<T>` |

**Rule of thumb:** start at use-case level. Promote up only when a second user actually appears — not preemptively.

---

## NXT-008 — File naming

| Type | Convention | Example |
|---|---|---|
| Component | `PascalCase.tsx` | `BookAppointmentForm.tsx` |
| Hook | `use-kebab-case.ts` | `use-video-room.ts` |
| Business logic | `verb-kebab-case.ts` | `check-drug-interactions.ts` |
| API call | `verb-kebab-case.ts` | `issue-prescription.ts` |
| Schema | `<domain>.schema.ts` | `prescription.schema.ts` |
| Types (use case) | `types.ts` | `types.ts` |
| Types (capability) | `<domain>.types.ts` | `appointment.types.ts` |
| Constants | `constants.ts` or `<domain>.constants.ts` | `controlled-substances.constants.ts` |
| Test | `<name>.test.ts` | `verify-dosage.test.ts` |

Component names must be **domain-qualified**, not generic. `AppointmentCard`, not `Card`. `ConfirmDeleteModal`, not `Modal`. A name that could belong to any feature is too generic.

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| `src/utils/` or `src/utils.ts` | Junk drawer — "utils" means "I didn't think about it" |
| `src/helpers.ts` | Same |
| `src/types.ts` (top-level mega-file) | Types belong next to their owner |
| `src/components/CheckoutForm.tsx` | Feature-specific code in a global folder |
| `src/services/AppointmentService.ts` | Top-level technical folder, not a business capability |
| `src/models/` | Top-level technical folder |
| Component file at use-case root | Must be in `components/` |
| Hook file at use-case root | Must be in `hooks/` |
| Business logic at use-case root | Must be in `lib/` |
| Deep imports past `index.ts` | Breaks encapsulation |
| Business logic in `app/` (routing layer) | `app/` should be thin |
| Component named `Card`, `Modal`, `Selector` | Too generic; require domain qualifier |

---

## Review checklist

```
Top-level (src/)
  □ Folders are business capabilities (nouns)
  □ No components/, hooks/, lib/, services/, models/ at the top level
  □ app/ is thin — only routing
  □ shared/ contains only code used by 3+ capabilities

Per capability
  □ Subfolders are use cases (verb phrases)
  □ Has an index.ts public API
  □ Cross-capability imports go through index.ts only

Per use case (MANDATORY SHAPE)
  □ Components live in components/ — never at the root
  □ Hooks live in hooks/ — never at the root
  □ Business logic lives in lib/ — never at the root
  □ Server calls live in api/ — never at the root
  □ Validation lives in schemas/ — never at the root
  □ Has types.ts and index.ts at the root
  □ No empty folders
  □ No utils.ts or helpers.ts anywhere

Naming
  □ Components: PascalCase.tsx, domain-qualified
  □ Hooks: use-kebab-case.ts
  □ Logic/api/schema files: verb-kebab-case.ts
  □ Types: <domain>.types.ts at capability level
```
