# Flask — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Flask. The decomposition model — business → feature →
sub-feature → unit, one job per file, front doors, Rule of Three, no junk drawers — lives in
`common/structure.md`, loaded alongside this. Read that first; this file is just the Flask specifics.

## Outer shell

Flask imposes no layout — it's unopinionated by design. The convention here is **one feature package per
capability, each exposing a Blueprint, all wired together by an application factory**. Nothing in the
framework enforces this; discipline is the only enforcement. Business folders are yours to name, so they
go at the top of your app package (`<app>/<feature>/…`) and follow `common/structure.md` inside.

## Naming

- **Files and modules** — `snake_case.py`, named by the job: `<verb>_<noun>.py`. Not `utils.py`, not `helpers.py`.
- **Feature packages** — `snake_case` (`<feature>/`).
- **Classes** (models, schemas, exceptions, config) — `PascalCase`. Models are singular nouns (`<Entity>`);
  exceptions end in `Error`; config classes end in `Config` (`ProductionConfig`).
- **View and service functions** — `snake_case`, verb-led (`<verb>_<noun>`).

## Front door

A feature package's `__init__.py` is its public surface. It defines the Blueprint and re-exports the
symbols other features may use; outsiders import through it, never past it into `routes.py` or internals.

```python
# <feature>/__init__.py
from flask import Blueprint

bp = Blueprint('<feature>', __name__)

# Routes import at the bottom: importing them registers the view functions on `bp`.
# The placement is deliberate (bp must exist first), hence the noqa.
from . import routes  # noqa: E402, F401

# Public re-exports for other features:
from . import service, schemas  # noqa: E402
```

Other features call `from ..<feature> import service` and use service functions — not `..<feature>.routes`,
not another feature's models directly.

## Flask specifics

- **Application factory, always.** Never `app = Flask(__name__)` at module level; that binds the
  app to one configuration and breaks testing. Build it in a `create_app(config)` function that loads
  config, initializes extensions, registers Blueprints, and registers the error handler. Tests build their
  own app with test config; production calls `create_app(ProductionConfig)` from a `wsgi.py` entrypoint.

- **One Blueprint per feature, registered only by the factory.** The feature's `__init__.py`
  defines `bp` and imports its routes at the bottom (see Front door — the `# noqa` is required because the
  import must follow `bp`). `create_app()` is the single place that registers every Blueprint with its URL
  prefix, so it grows with the feature count, never with logic.

  ```python
  def create_app(config=Config):
      app = Flask(__name__)
      app.config.from_object(config)
      db.init_app(app)
      app.register_blueprint(<feature>_bp, url_prefix='/<feature>')
      register_error_handlers(app)
      return app
  ```

- **Validate at the boundary; never trust `request.get_json()`.** Flask does no validation. The
  view function loads the raw body through a schema (Marshmallow or Pydantic) and passes typed data on; the
  service never sees a raw request. These schemas are the allowed hybrid "shape + validation" classes
  (`common/objects-and-data.md` OD-005). Likewise serialize responses through a schema — never return a
  SQLAlchemy model straight out of a view.

- **Extensions defined once, initialized in the factory.** Flask extensions (Flask-SQLAlchemy,
  Flask-Migrate, Flask-Login, …) are stateful singletons. Construct them once in `extensions.py` with no
  app, then call `.init_app(app)` inside `create_app`. Models may import `db` because they bind at app-init;
  ad-hoc scripts must push an `app_context()` before touching it.

- **One centralized error handler.** Define an `AppError` hierarchy (each subclass carries its own
  `code` and `status_code`), and register the handlers on the app in the factory. Views raise a domain error
  (`raise NotFoundError(...)`); the handler shapes the response. No scattered `return jsonify({...}), 400` in
  views — that fragments error shapes. This is `common/error-handling.md` EH-002 applied to Flask.

- **One config class per environment.** `app.config` is a plain dict; drive it from typed config
  classes (`Config` base, then `DevelopmentConfig` / `ProductionConfig` / `TestingConfig`), or
  `pydantic-settings`. Required env vars resolve once at class load. No `os.environ.get(...)` sprinkled
  through feature code.
