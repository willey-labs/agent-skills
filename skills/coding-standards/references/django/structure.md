# Django — Architecture

The chosen pattern for Django projects (including Django REST Framework): **stock Django apps** as the unit of feature isolation, with a **services layer** added between views and models for orchestration. Each Django app is one business capability; the framework's app boundary is the public API.

---

## The philosophy in one sentence

> One Django app per business capability. Models, views/viewsets, serializers, urls, and tests live inside the app. A `services.py` module sits between views and models for orchestration. Cross-app dependencies go through the app's public surface.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. Django's idiomatic per-app layout already enforces folder-as-module and per-app isolation; what we add is the **services layer** (Django doesn't ship one by default) and rules for splitting `views.py` / `models.py` once they grow. Read `common/structure.md` first.

---

## Mandatory shape

```
project_root/
  manage.py
  pyproject.toml                       (or requirements.txt + setup.cfg)

  config/                              ← project-level configuration
    __init__.py
    settings/
      __init__.py
      base.py
      development.py
      production.py
      test.py
    urls.py                            ← root URLconf — wires app URLs
    asgi.py
    wsgi.py

  appointments/                        ← 📅 DJANGO APP = BUSINESS CAPABILITY
    __init__.py
    apps.py                            ← AppConfig
    admin.py                           ← Django admin registration
    models.py                          ← (or models/ package once it grows)
    serializers.py                     ← DRF serializers (or serializers/)
    views.py                           ← (or views/ package once it grows)
    viewsets.py                        ← DRF viewsets (when using DRF)
    urls.py                            ← app-local URL patterns
    permissions.py                     ← DRF permission classes
    services.py                        ← orchestration / use cases
    selectors.py                       ← read-side queries (the project's choice)
    tasks.py                           ← Celery tasks
    signals.py                         ← Django signals
    migrations/
      0001_initial.py
    templates/appointments/            ← namespaced templates (when used)
    tests/
      __init__.py
      test_views.py
      test_services.py
      test_models.py

  prescriptions/                       ← 💊 DJANGO APP
    ...

  identity/                            ← 🔐 DJANGO APP (usually built on django.contrib.auth)
    ...

  shared/                              ← cross-cutting (3+ apps)
    __init__.py
    apps.py
    middleware.py                      ← custom middleware
    exceptions.py                      ← custom exception classes + handler
    pagination.py                      ← DRF pagination defaults
    permissions.py                     ← shared permission base classes
    storage.py                         ← storage backend wrappers
    types.py                           ← only truly app-wide types
```

---

## DJ-001 — One Django app, one business capability

Django apps are the framework's unit of feature isolation. Use them. **One app = one business capability**, not "one app per technical layer."

| ✅ Right | ❌ Wrong |
|---|---|
| `appointments/`, `prescriptions/`, `billing/`, `identity/` | `api/`, `models/`, `views/` as top-level apps |
| `core/` or `shared/` for genuinely cross-cutting code | `helpers/` app holding miscellaneous things |
| `apps/` or top-level layout, your choice — keep the names business-shaped | A single `myproject/` app containing every model and view |

If you have one giant app with 40 models, it's not really an app — it's a project with no isolation. Split by capability.

---

## DJ-002 — Add a services layer

Django ships with two layers: **views** (HTTP boundary) and **models** (data + Active-Record-ish behavior). For anything beyond trivial CRUD this is too thin — orchestration logic ends up in either views (mixing HTTP with business rules) or models (god-class anti-pattern).

**Add a `services.py` module per app** (or a `services/` package once it grows). Services are plain functions or classes that orchestrate use cases:

```python
# appointments/services.py
from django.db import transaction
from billing.services import charge_card
from notifications.services import send_confirmation
from .models import Appointment

@transaction.atomic
def book_appointment(*, patient, doctor, slot, payment_method) -> Appointment:
    if not slot.is_available():
        raise SlotUnavailableError(slot.id)

    appointment = Appointment.objects.create(
        patient=patient, doctor=doctor, slot=slot, status=Appointment.Status.PENDING
    )
    charge_card(payment_method, appointment.fee)
    appointment.confirm()
    send_confirmation(appointment)
    return appointment
```

The view becomes a thin adapter:

```python
# appointments/views.py (DRF)
class BookAppointmentView(APIView):
    permission_classes = [IsAuthenticatedPatient]

    def post(self, request):
        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = services.book_appointment(**serializer.validated_data)
        return Response(AppointmentResponseSerializer(appointment).data, status=201)
```

**The split:**

| Layer | Owns | Does NOT own |
|---|---|---|
| View / Viewset | HTTP parsing, permission checks, response shaping | Business rules, multi-step workflows |
| Serializer | Wire shape, validation rules at the boundary | Side effects, business decisions |
| Service | Orchestration, transaction boundary, cross-model coordination | HTTP details, presentation concerns |
| Selector (optional) | Read-side queries that don't belong on a manager/queryset | Mutations |
| Model | Invariants tied to the model's own data, `save()` hooks, scopes (managers) | Workflows that touch multiple aggregates |

This is the [HackSoftware "Django Styleguide"](https://github.com/HackSoftware/Django-Styleguide) pattern — a widely-used convention for non-trivial Django apps, not a framework default (Django ships no services layer).

---

## DJ-003 — Models own behavior tied to their data; not cross-cutting workflows

Same rule as `references/laravel/structure.md` LRV-003 and `references/csharp/structure.md` CS-003. **Framework-boundary carve-out applies** — see `common/objects-and-data.md` OD-005. Django models inherit from `django.db.models.Model` and carry framework decorators / manager bindings; they're allowed to be "hybrid" classes in that framework sense.

```python
# ✅ Good — behavior about the appointment's own data lives on the model
class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        CONFIRMED = 'confirmed'
        CANCELLED = 'cancelled'

    status = models.CharField(max_length=16, choices=Status.choices)
    scheduled_at = models.DateTimeField()

    def is_cancellable(self) -> bool:
        return self.status != self.Status.CANCELLED and self.scheduled_at > timezone.now()

    def cancel(self, reason: str) -> None:
        if not self.is_cancellable():
            raise CannotCancelError()
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.save()
```

```python
# ❌ Bad — cross-cutting workflow on the model
class Appointment(models.Model):
    def book(self):
        # ...validate slot, charge card, send confirmation, dispatch job...
        # This belongs in services.book_appointment, not on the model.
```

Custom managers and querysets are the right home for read-side query logic:

```python
class AppointmentQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status=Appointment.Status.CANCELLED)

    def for_patient(self, patient):
        return self.filter(patient=patient)

class Appointment(models.Model):
    objects = AppointmentQuerySet.as_manager()
```

---

## DJ-004 — Serializers at the boundary; never trust raw request data

DRF serializers are the equivalent of NestJS DTOs and Laravel Form Requests. They:

- Validate the wire shape.
- Translate field names to the project's conventions.
- Are responsible for input shape **and** output shape (request + response serializers when the two differ).

```python
# appointments/serializers.py
class BookAppointmentSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    slot_id = serializers.UUIDField()
    payment_method_id = serializers.UUIDField()

    def validate_slot_id(self, value):
        if not Slot.objects.filter(pk=value, is_open=True).exists():
            raise serializers.ValidationError('slot_unavailable')
        return value

class AppointmentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['id', 'status', 'scheduled_at', 'doctor_id', 'patient_id']
```

The view never passes raw `request.data` to a service.

**Pure-Django (non-DRF) projects** use `django.forms.Form` / `ModelForm` for the same purpose at the view boundary. The principle holds.

---

## DJ-005 — `services.py` becomes `services/` when it grows

A flat `services.py` is fine until a feature has 5+ orchestration functions. Then split:

```
appointments/
  services/
    __init__.py            ← re-exports the public surface
    booking.py
    cancellation.py
    rescheduling.py
    reminders.py
```

The `__init__.py` declares the app's service public surface, mirroring the index.ts convention from `common/structure.md` ST-002:

```python
# appointments/services/__init__.py
from .booking import book_appointment
from .cancellation import cancel_appointment
from .rescheduling import reschedule_appointment

__all__ = ['book_appointment', 'cancel_appointment', 'reschedule_appointment']
```

Same rule for `views/`, `models/`, `serializers/` when they grow.

---

## DJ-006 — Cross-app dependencies are explicit and one-way

If `appointments/` needs something from `identity/`, import via the app's public surface (`from identity.services import ...`). Internal imports across apps (`from identity.models.user_internal import ...`) are forbidden — they break the app-boundary contract that lets you reuse the app elsewhere.

**The dependency direction matters.** `appointments/` may depend on `identity/`; `identity/` should not depend on `appointments/`. Identity is foundational. Decide which apps are foundational at the start and document them in `config/settings/base.py` (or an `ARCHITECTURE.md`) so contributors know.

**Enforce with `import-linter`:**

```toml
# .importlinter
[importlinter:contract:appointments-do-not-depend-on-other-features]
type = forbidden
source_modules = ["appointments"]
forbidden_modules = ["billing", "prescriptions"]   # except via well-defined boundaries
```

---

## DJ-007 — Migrations are part of the feature

Migrations live in `<app>/migrations/`. Commit them with the model change that produced them. **Never edit a merged migration** (regenerate or write a follow-up); migrations are append-only history.

**Squash migrations periodically** when the chain gets long (`python manage.py squashmigrations`). Long migration chains slow down test setup and confuse new contributors trying to understand schema history.

**Data migrations** (`RunPython`) are appropriate for one-off data shape changes. They are *not* the place to seed business data — that belongs in fixtures or management commands.

---

## DJ-008 — Custom exceptions; one handler at the boundary

The Django/DRF default of "raise random exceptions and hope" is not enough. Define an app-specific exception base class and a centralized exception handler:

```python
# shared/exceptions.py
class AppError(Exception):
    code: str = 'app_error'
    status_code: int = 400

class NotFoundError(AppError):
    code = 'not_found'
    status_code = 404

# DRF custom handler
def custom_exception_handler(exc, context):
    if isinstance(exc, AppError):
        return Response({'error': {'code': exc.code, 'message': str(exc)}}, status=exc.status_code)
    return drf_default_handler(exc, context)
```

Register it in DRF settings (`REST_FRAMEWORK = {'EXCEPTION_HANDLER': '...'}`). For pure-Django, register the handler in `urls.py` via `handler500`, `handler404`, `handler403`.

This is `common/error-handling.md` EH-002 — translate raw exceptions at the boundary.

---

## DJ-009 — Settings split for env safety

Never load production settings in development. Use a settings package:

```
config/settings/
  base.py          ← shared
  development.py   ← from .base import *; overrides
  production.py    ← from .base import *; overrides + sanity-checks env
  test.py
```

`DJANGO_SETTINGS_MODULE=config.settings.production` is set per environment. **Validate required env at startup** — settings files should `raise ImproperlyConfigured` if a required variable is missing or unsafe. Don't let the app boot with `DEBUG=True` in production silently.

---

## DJ-010 — Naming

| Type | Convention | Example |
|---|---|---|
| Django app | `snake_case`, plural noun | `appointments/`, `prescriptions/`, `billing/` |
| Model | `PascalCase`, singular | `Appointment`, `Prescription`, `Order` |
| Model field | `snake_case` | `scheduled_at`, `customer_id` |
| View / Viewset | `PascalCase`, ends in `View` or `ViewSet` | `BookAppointmentView`, `AppointmentViewSet` |
| Serializer | `PascalCase`, ends in `Serializer` | `BookAppointmentSerializer` |
| Service function | `snake_case`, verb-led | `book_appointment`, `cancel_appointment` |
| Manager / queryset | `PascalCase`, ends in `Manager` or `QuerySet` | `AppointmentQuerySet` |
| Custom permission | `PascalCase` | `IsAppointmentOwner` |
| URL name | `kebab-case` or `snake_case` (consistent project-wide) | `book-appointment` |
| Test module | `test_<thing>.py` | `test_services.py`, `test_views.py` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| `views.py` with business logic and direct ORM mutations | Use a service |
| Models with workflow methods (`book`, `charge`, `notify`) | Cross-cutting orchestration belongs in services |
| Fat serializers doing business validation across multiple objects | Move multi-object validation to the service |
| `core/` or `utils/` app holding miscellaneous things | Junk drawer (see `common/structure.md` ST-005) |
| Cross-app imports of internal modules (`from billing.models.invoice_internal import ...`) | Goes through public surface only (see `common/structure.md` ST-003) |
| One giant `myproject/` app with everything | Split into capability apps |
| `settings.py` with hardcoded secrets or `DEBUG=True` in production paths | Use environment validation |
| Editing a merged migration | Migrations are append-only — write a follow-up |
| `from .models import *` in `__init__.py` for "convenience" | Hides the public surface; be explicit |
| Direct ORM calls inside a Celery task that re-implements service logic | Tasks should call services, not duplicate them |
| Global `select_related` / `prefetch_related` everywhere "just in case" | Optimize where measurement shows N+1 — not preemptively |

---

## Review checklist

```
Structure
  □ Top-level apps are business capabilities, not technical layers
  □ Each app has services.py (or services/) when it has any orchestration
  □ shared/ contains only code used by 3+ apps
  □ Settings split: base/development/production/test

Per app
  □ Models own behavior about their own data
  □ Services own cross-cutting workflows and transactions
  □ Serializers validate at the boundary; never raw request.data into services
  □ URLconf is per-app and wired from config/urls.py

Cross-app
  □ Imports go through public surfaces (no reaching into other apps' internals)
  □ Dependency direction documented (foundational apps explicit)

Exception handling
  □ Custom AppError hierarchy
  □ Central exception handler translates to API responses
  □ No bare `except:` blocks

Migrations
  □ Migrations live with the app
  □ No editing of merged migrations
  □ Long chains squashed periodically
```
