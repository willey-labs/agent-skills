# Django — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Django (including Django REST Framework). The decomposition model
— business → feature → sub-feature → unit, one job per file, front doors, the ST rules — lives in
`common/structure.md`, loaded alongside this. Read that for how to organize the inside of any folder; this
file is just the Django specifics.

## Outer shell

Like Laravel, Django keeps its framework skeleton — but the unit of isolation is the **Django app**, and
that app's folder name **is** yours to pick (`<capability>/`). So business folders sit at the top, one app
per capability, and inside each app you follow `common/structure.md`.

A Django app is one business capability — not one technical layer. Its standard modules all live inside the
app: `models.py`, `views.py`, `serializers.py`, `urls.py`, `migrations/`, and a `tests/` package beside the
code it tests. Add one module Django doesn't ship: a **services layer** for orchestration.

```
<capability>/                ← a Django app == one business capability
  models.py                  ← (or models/ once it earns a package)
  views.py                   ← thin HTTP adapters (or views/)
  serializers.py             ← DRF boundary validation (or serializers/)
  services.py                ← orchestration / use cases (or services/)
  urls.py                    ← app-local URLconf, wired from the root urls.py
  migrations/                ← ships with the app
  tests/                     ← test_services.py, test_views.py, …
```

A second capability is a second top-level app. Genuinely cross-cutting code (used by 3+ apps) goes in a
`shared/` app — never a `core/` or `utils/` junk drawer (ST-005).

## Naming

- **Apps, modules, files, fields** — `snake_case`: `<capability>/`, `book_<noun>.py`, `scheduled_at`.
- **Models, views, serializers, managers, permissions** — `PascalCase`, suffixed by what they are:
  `<Noun>` (model), `<Verb><Noun>View` / `<Noun>ViewSet`, `<Verb><Noun>Serializer`, `<Noun>QuerySet`.
- **Service functions** — `snake_case`, verb-led: `book_<noun>`, `cancel_<noun>`.

## Front door

Django has no `index` file. An app's public surface is its **services and its public models** — other apps
import those, never another app's internal modules (ST-003). When `services.py` grows into a `services/`
package, its `__init__.py` re-exports the public functions and everything else stays private (ST-002).

## Django specifics

- **One app, one capability.** The app boundary is the unit of feature isolation. One giant app
  with 40 models is a project with no isolation — split it by capability.

- **A services layer sits between views and models.** Django ships only views (HTTP) and models
  (data). Orchestration — multi-step workflows, transaction boundaries, cross-model coordination — goes in
  plain `snake_case` functions in `services.py`. The view parses and permits; the service decides and acts.

- **Model methods for the model's own data; services for workflows.** Behavior about one record's
  own state (`<entity>.cancel(reason)`, query scopes on a custom manager) lives on the model. Anything
  that touches multiple models or external systems (charge a card, send mail, dispatch a job) is a service.
  The model must not grow into a god class owning cross-cutting workflows.

- **Serializers validate at the boundary; the view maps fields to the service.** A DRF serializer
  (or a `forms.Form` in pure Django) validates the wire shape before anything else runs. The view then maps
  `validated_data` to the service's *actual* parameters by name — it does not blindly spread `**validated_data`
  into the service. Serializer field names and service parameters drift apart over time; spreading mismatched
  keys is how a renamed field silently passes the wrong argument or raises a confusing `TypeError`.

- **Migrations are part of the app.** They live in `<app>/migrations/` and commit with the model
  change that produced them. Never edit a merged migration — it's append-only history; write a follow-up or
  regenerate. Squash long chains periodically.

- **Settings split per environment.** Use a `config/settings/` package (`base.py` plus
  `development.py` / `production.py` / `test.py`), selected by `DJANGO_SETTINGS_MODULE`. Validate required
  env at startup — raise `ImproperlyConfigured` on a missing or unsafe variable rather than booting with
  `DEBUG=True` in production.
