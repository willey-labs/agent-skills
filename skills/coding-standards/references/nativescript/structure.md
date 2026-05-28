# NativeScript — Architecture

The chosen pattern for NativeScript (JavaScript/TypeScript native mobile) projects: **flat business folders** — top-level folders inside `app/` are business capabilities, not technical layers. NativeScript apps are screen-and-navigation-centric; flat capability folders keep one capability's code together without an extra `features/` wrapper.

---

## The philosophy in one sentence

> Top-level folders inside `app/` are business capabilities. Each folder owns all its layers — view, view-model, services, types — and exposes them through `index.ts`. Cross-capability dependencies go through public APIs.

---

## Mandatory shape

```
app/
  app.ts                            ← bootstrap
  app-root.xml                      ← root navigation frame
  app.css                           ← global styles (sparingly)

  appointments/                     ← 📅 BUSINESS CAPABILITY
    views/                          ← screens / pages
      appointment-list-page.xml
      appointment-list-page.ts
      appointment-list-page-view-model.ts
      appointment-detail-page.xml
      appointment-detail-page.ts
      appointment-detail-page-view-model.ts
    components/                     ← shared within this capability
      appointment-card.xml
      appointment-card.ts
      appointment-card-view-model.ts
    services/                       ← API calls, persistence
      appointment-service.ts
      appointment-repository.ts
    models/                         ← capability-local types
      appointment.model.ts
    types.ts
    index.ts                        ← 🚪 public API

  prescriptions/                    ← 💊 BUSINESS CAPABILITY
    views/
    components/
    services/
    models/
    types.ts
    index.ts

  identity/                         ← 🔐 BUSINESS CAPABILITY
    views/
      sign-in-page.xml
      sign-in-page.ts
      sign-in-page-view-model.ts
    services/
      auth-service.ts
    types.ts
    index.ts

  shared/                           ← used by 3+ capabilities
    ui/                             ← shared XML components
      loading-indicator.xml
      loading-indicator.ts
      empty-state.xml
      empty-state.ts
    services/
      http-client.ts
      storage.ts                    ← ApplicationSettings wrapper
      logger.ts
    platform/                       ← Android/iOS specific helpers
      permissions.ts
      device-info.ts
    types/
      global.ts

  fonts/                            ← per NativeScript convention
  assets/
    images/
    icons/
```

---

## NS-001 — Top-level folders are business capabilities

| Allowed at the top of `app/` | Forbidden |
|---|---|
| ✅ Business capability folders (`appointments/`, `prescriptions/`, `identity/`) | ❌ `app/views/` (all screens together) |
| ✅ `shared/` | ❌ `app/services/` (all services together) |
| ✅ `assets/`, `fonts/` (NativeScript convention) | ❌ `app/models/` (all models together) |
| ✅ `app.ts`, `app-root.xml`, `app.css` | ❌ `app/utils.ts` |
|  | ❌ `app/features/` wrapper folder |

To find everything related to "appointments," open `app/appointments/`. One folder. No wrapper.

---

## NS-002 — Page-and-ViewModel trio stays together

NativeScript pages come as a three-file unit:

```
appointments/views/
  appointment-list-page.xml         ← markup
  appointment-list-page.ts          ← code-behind (page event handlers)
  appointment-list-page-view-model.ts  ← MVVM view model (the state + behavior)
```

These three files always live together — never split into `views/xml/`, `views/ts/`, `view-models/`. Co-location means a developer opens the folder and sees the whole screen.

**Naming convention:** `kebab-case-page.*` for full pages, `kebab-case.*` for reusable components within the feature.

---

## NS-002b — Capabilities never import from each other

Cross-capability deep imports are forbidden. If `appointments/` needs something from `identity/`, route it through `identity/index.ts` — and only when the export was deliberately added there.

```ts
// ✅ Allowed
import { AuthService } from '@/identity'

// ❌ Forbidden — deep import
import { AuthService } from '@/identity/services/auth-service'
```

Anything used by 3+ capabilities moves to `shared/`.

---

## NS-003 — View models hold state and behavior; pages dispatch events

A NativeScript page's code-behind (`*.ts` next to the `.xml`) should be small — typically just creating the view model and exposing event handlers. **Business logic lives in the view model**, not the page.

```ts
// ❌ Bad — business logic in the page
// appointment-list-page.ts
export function onLoaded(args: EventData) {
    const page = args.object as Page
    const appointments = await fetch('https://api/...')  // DON'T fetch here
    const filtered = appointments.filter(a => a.status === 'pending')  // DON'T transform here
    page.bindingContext = { appointments: filtered }
}

// ✅ Good — page wires up the view model; view model does the work
// appointment-list-page.ts
import { AppointmentListViewModel } from './appointment-list-page-view-model'

export function onLoaded(args: EventData) {
    const page = args.object as Page
    page.bindingContext = new AppointmentListViewModel()
}

// appointment-list-page-view-model.ts
export class AppointmentListViewModel extends Observable {
    private appointmentService = new AppointmentService()

    async load(): Promise<void> {
        this.set('isLoading', true)
        this.set('appointments', await this.appointmentService.listPending())
        this.set('isLoading', false)
    }
}
```

The page is a thin adapter between NativeScript's lifecycle and your view model.

---

## NS-004 — Services own external interactions

API calls, persistence (ApplicationSettings, SQLite), and platform APIs live in the capability's `services/` folder — never inside view models or pages directly.

```
appointments/services/
  appointment-service.ts            ← HTTP — talks to the backend
  appointment-repository.ts         ← local cache / persistence
```

View models import services; services import the shared HTTP client and storage layer. This is `code-principles.md` DP-005 (Dependency Inversion) at small scale — view models depend on a service abstraction, not on `fetch` directly.

**Why this matters more on mobile:** offline-first behavior, retry logic, request deduplication, and error transformation all belong in the service layer where they can be reused and tested without spinning up a page.

---

## NS-005 — Platform-specific code lives in `shared/platform/` or in `.android.ts` / `.ios.ts`

NativeScript supports platform-suffix files: `device-info.android.ts` and `device-info.ios.ts` with a shared `device-info.d.ts` declaration. Use this when behavior diverges between iOS and Android.

```
shared/platform/
  permissions.ts                    ← cross-platform interface
  permissions.android.ts            ← Android implementation
  permissions.ios.ts                ← iOS implementation
  device-info.ts
  device-info.android.ts
  device-info.ios.ts
```

**Do not** scatter `if (isAndroid)` / `if (isIOS)` branches across feature code. Hide the platform difference behind a single import.

---

## NS-006 — `shared/` requires three users

Same Rule of Three as the rest of this skill. Move a service, component, or model to `shared/` only when 3+ capabilities actually use it.

| Allowed in `shared/` | Forbidden |
|---|---|
| ✅ `shared/ui/` — reusable XML components (loading, empty state, error) | ❌ `shared/utils.ts` |
| ✅ `shared/services/http-client.ts` (used by every capability's service) | ❌ A "shared" component only one capability renders |
| ✅ `shared/platform/*` — cross-platform helpers | ❌ Mega-file `shared/types.ts` |
| ✅ `shared/services/storage.ts` (ApplicationSettings wrapper) |  |

---

## NS-007 — Navigation lives at composition points, not inside view models

NativeScript's `Frame.navigate()` couples a view model to a route. Keep navigation **out of** view models when possible — instead, expose intent (events, callbacks) and let the page-level code handle the navigation.

```ts
// ❌ Bad — view model knows about navigation
class SignInViewModel extends Observable {
    async signIn() {
        await this.authService.signIn(...)
        Frame.topmost().navigate('features/appointments/views/appointment-list-page')
    }
}

// ✅ Good — view model emits intent; page navigates
class SignInViewModel extends Observable {
    onSignedIn?: () => void

    async signIn() {
        await this.authService.signIn(...)
        this.onSignedIn?.()
    }
}

// sign-in-page.ts
export function onLoaded(args: EventData) {
    const page = args.object as Page
    const vm = new SignInViewModel()
    vm.onSignedIn = () => Frame.topmost().navigate('features/appointments/views/appointment-list-page')
    page.bindingContext = vm
}
```

This keeps view models testable (no Frame dependency) and makes the navigation graph visible at the page level.

---

## NS-008 — File and folder naming

| Type | Convention | Example |
|---|---|---|
| Capability folder | `kebab-case`, plural noun | `appointments/`, `prescriptions/` |
| Page (XML + TS + VM) | `kebab-case-page.*` | `appointment-list-page.xml` |
| Reusable component within capability | `kebab-case.xml` + `.ts` | `appointment-card.xml` |
| View model | `*-view-model.ts` | `appointment-list-page-view-model.ts` |
| Service | `kebab-case-service.ts` | `appointment-service.ts` |
| Repository | `kebab-case-repository.ts` | `appointment-repository.ts` |
| Model / type file | `*.model.ts` or `types.ts` | `appointment.model.ts`, `types.ts` |
| Public API of folder | `index.ts` | (always) |
| Platform-specific | `*.android.ts` / `*.ios.ts` | `permissions.ios.ts` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `app/views/`, `app/services/`, `app/models/` | Package by layer — find every "appointments" file by jumping between folders |
| Business logic in `*-page.ts` (the code-behind) | View model is the right place |
| `fetch()` / API call directly inside a view model or page | Should go through a service |
| `Frame.navigate()` calls inside view models | Couples VM to routing; harder to test |
| `if (isAndroid)` branches scattered through capability code | Use platform-suffix files |
| `shared/utils.ts` or `shared/helpers.ts` | Junk drawer |
| A capability folder with no `index.ts` | No public API; encourages deep imports |
| Cross-capability deep imports (`identity/services/auth-service`) | Should go through `identity/index.ts` |
| `app/features/` wrapper folder | Adds a useless extra level — top of `app/` already screams the business |

---

## Review checklist

```
Structure
  □ Top-level app/ folders are business capabilities (no features/ wrapper)
  □ Each capability has views/, services/, and an index.ts
  □ shared/ contains only code used by 3+ capabilities
  □ No app/views/, app/services/, app/models/ at the top level

Per page
  □ XML + page TS + view model live in the same folder
  □ Page TS is thin — wires up view model, handles events
  □ Business logic lives in the view model

Services
  □ All API calls go through a service
  □ All persistence goes through a service/repository
  □ Platform differences hidden in shared/platform/ or .android.ts / .ios.ts

Imports
  □ Cross-capability imports go through index.ts
  □ No deep imports past index.ts
```
