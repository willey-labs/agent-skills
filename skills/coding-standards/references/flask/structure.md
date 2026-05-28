# Flask — Architecture

The chosen pattern for Flask projects: **package by feature, Blueprints per feature, application factory pattern**. Flask is unopinionated by design; like Express, the discipline below is the only enforcement.

---

## The philosophy in one sentence

> Application factory creates the Flask app. One Blueprint per business feature, registered by the factory. Each feature folder owns its blueprint, service, repository, and schemas. `shared/` holds infrastructure used by 3+ features.

---

## Builds on `common/structure.md`

This file specializes the universal structural rules in `references/common/structure.md`. Flask adds Blueprints as the framework-supported per-feature grouping, the application-factory pattern, and the request-context model. Read `common/structure.md` first.

---

## Mandatory shape

```
src/myapp/
  __init__.py                          ← create_app() — the application factory
  config.py                            ← config classes (Development, Production, Testing)
  extensions.py                        ← extension singletons (db, login_manager, migrate, ...)

  checkout/                            ← 🛒 FEATURE
    __init__.py                        ← exposes the feature's Blueprint as `bp`
    routes.py                          ← view functions / handlers
    service.py                         ← orchestration / use cases
    repository.py                      ← persistence
    schemas.py                         ← Marshmallow / Pydantic schemas
    models.py                          ← SQLAlchemy models (registered with shared db extension)
    exceptions.py                      ← feature-specific exceptions

  identity/                            ← 🔐 FEATURE
    __init__.py
    routes.py
    service.py
    schemas.py
    models.py
    auth.py                            ← login_required wrappers, session helpers

  products/
    ...

  shared/                              ← cross-cutting (3+ features)
    __init__.py
    errors.py                          ← AppError + Flask error handlers
    pagination.py
    cli.py                             ← Click commands registered with the app
    middleware.py
    types.py

migrations/                            ← Alembic migrations (Flask-Migrate)
tests/                                 ← integration / e2e — unit tests live next to source

wsgi.py                                ← production WSGI entrypoint: app = create_app('production')
```

---

## FL-001 — Use the application factory pattern

Never define `app = Flask(__name__)` at module level. That binds the app to a single configuration and breaks testing.

```python
# myapp/__init__.py
from flask import Flask
from .config import Config
from .extensions import db, migrate, login_manager
from .shared.errors import register_error_handlers
from .checkout import bp as checkout_bp
from .identity import bp as identity_bp
from .products import bp as products_bp

def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(checkout_bp, url_prefix='/checkout')
    app.register_blueprint(identity_bp, url_prefix='/identity')
    app.register_blueprint(products_bp, url_prefix='/products')

    register_error_handlers(app)
    return app
```

Tests create their own app instance with test config. Production starts via `wsgi.py`:

```python
# wsgi.py
from myapp import create_app
from myapp.config import ProductionConfig
app = create_app(ProductionConfig)
```

---

## FL-002 — One Blueprint per feature

Each feature folder's `__init__.py` defines and exports the Blueprint, and the routes file registers view functions on it:

```python
# checkout/__init__.py
from flask import Blueprint

bp = Blueprint('checkout', __name__)

# Importing routes at the bottom ensures view functions register on `bp`.
from . import routes  # noqa: E402, F401
```

```python
# checkout/routes.py
from flask import request, jsonify
from . import bp, service, schemas

@bp.route('/orders', methods=['POST'])
def place_order():
    request_data = schemas.PlaceOrderRequest().load(request.get_json())
    order = service.place_order(request_data)
    return schemas.OrderResponse().dump(order), 201
```

`create_app()` registers each Blueprint with a URL prefix. `create_app()` doesn't grow with logic — only with the count of features.

---

## FL-003 — Validate at the boundary; never trust request.get_json()

Flask gives you no validation. Use Marshmallow (the traditional choice) or Pydantic (modern), and validate at the route handler. The service never sees raw `request.get_json()`.

```python
# checkout/schemas.py
from marshmallow import Schema, fields, validate

class OrderItemInput(Schema):
    product_id = fields.UUID(required=True)
    quantity = fields.Integer(required=True, validate=validate.Range(min=1))

class PlaceOrderRequest(Schema):
    items = fields.List(fields.Nested(OrderItemInput), required=True, validate=validate.Length(min=1))

class OrderResponse(Schema):
    id = fields.UUID()
    status = fields.String()
    total = fields.Integer()
```

The schema validates incoming JSON, raises `marshmallow.ValidationError` on failure, and feeds typed data into the service.

**Framework-boundary carve-out (see `common/objects-and-data.md` OD-005).** Marshmallow / Pydantic schemas, like Flask's SQLAlchemy models, are intentionally "hybrid" classes — they carry shape and validation behavior. That's allowed.

---

## FL-004 — Services orchestrate; repositories persist

Same three-layer split as the other backend frameworks. Flask just doesn't enforce it.

```python
# checkout/service.py
from .repository import CheckoutRepository
from .exceptions import EmptyOrderError

def place_order(data: dict) -> Order:
    if not data['items']:
        raise EmptyOrderError()
    return CheckoutRepository.create_order(data)
```

```python
# checkout/repository.py
from ..extensions import db
from .models import Order

class CheckoutRepository:
    @staticmethod
    def create_order(data: dict) -> Order:
        order = Order(...)
        db.session.add(order)
        db.session.commit()
        return order
```

**The split:**

| Layer | Owns | Does NOT own |
|---|---|---|
| Route (view function) | HTTP parsing, response shaping, calling service | Business rules, DB access |
| Service | Orchestration, transaction boundary | HTTP details, raw SQL |
| Repository | Persistence per feature/aggregate | Business rules |

**Forbidden:** view functions calling `db.session.query(...)` directly — that's skipping the service and repository layers.

---

## FL-005 — Extensions in one place, initialized in the factory

Flask extensions (Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-Mail, etc.) are stateful singletons. Define them once in `extensions.py`, init them inside `create_app`:

```python
# myapp/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
```

```python
# myapp/__init__.py — inside create_app
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
```

**Forbidden:** importing `db` from any feature without `current_app` context active. Models can import `db` because they're registered at app-init time; ad-hoc scripts must call `create_app().app_context().push()` before touching the DB.

---

## FL-006 — Centralized error handling

Define a custom error hierarchy and register handlers with the Flask app:

```python
# shared/errors.py
class AppError(Exception):
    code = 'app_error'
    status_code = 400

class NotFoundError(AppError):
    code = 'not_found'
    status_code = 404

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({'error': {'code': err.code, 'message': str(err)}}), err.status_code

    @app.errorhandler(MarshmallowValidationError)
    def handle_validation(err):
        return jsonify({'error': {'code': 'validation_error', 'fields': err.messages}}), 400
```

Routes raise `NotFoundError(...)`. **Forbidden:** `return jsonify({...}), 400` scattered across routes. That bypasses the central handler and makes error shapes inconsistent.

This is `common/error-handling.md` EH-002 applied to Flask.

---

## FL-007 — Configuration via config classes

Flask's `app.config` is a dict. Drive it from typed config classes (or `pydantic-settings`):

```python
# myapp/config.py
import os

class Config:
    SQLALCHEMY_DATABASE_URI: str = os.environ['DATABASE_URL']
    SECRET_KEY: str = os.environ['SECRET_KEY']
    JSON_SORT_KEYS = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
```

**Forbidden:** `os.environ.get(...)` scattered through feature code. Config lives in one place, validated at boot.

---

## FL-008 — Cross-feature dependencies via public surface

The feature's `__init__.py` is the public surface. Other features import `from ..checkout import service, schemas` — never `from ..checkout.routes import ...` (routes are not the public API).

```python
# checkout/__init__.py
from flask import Blueprint
bp = Blueprint('checkout', __name__)
from . import routes  # noqa: F401

# Public re-exports for other features:
from . import service, schemas  # noqa: E402
from .exceptions import EmptyOrderError, OrderNotFoundError  # noqa: E402
```

Most cross-feature use should be via service functions, not via direct database access. Identity is usually foundational — other features call `identity.service.get_user(...)` rather than reaching into `User.query`.

Enforce with `import-linter`.

---

## FL-009 — Naming

| Type | Convention | Example |
|---|---|---|
| Feature package | `snake_case`, plural | `checkout/`, `products/`, `users/` |
| Blueprint variable | `bp` (one per feature `__init__.py`) | `bp = Blueprint('checkout', __name__)` |
| View function | `snake_case`, verb-led | `place_order`, `cancel_order` |
| Service function | `snake_case`, verb-led | `place_order`, `charge_card` |
| Marshmallow schema | `PascalCase`, suffix `Request` / `Response` | `PlaceOrderRequest`, `OrderResponse` |
| Model | `PascalCase`, singular | `Order`, `Product`, `User` |
| Exception | `PascalCase`, ends in `Error` | `EmptyOrderError` |
| Config class | `PascalCase`, ends in `Config` | `ProductionConfig` |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Module-level `app = Flask(__name__)` | Breaks testing and config; use the factory |
| View functions with business logic or direct DB access | Use a service |
| Returning SQLAlchemy models directly | Use a Marshmallow/Pydantic dump schema |
| Inline `if not x: return jsonify({...}), 400` in views | Raise a domain exception; let the handler shape the response |
| `os.environ.get('X')` scattered through code | Use a Config class loaded once in the factory |
| Cross-feature deep imports (`from ..billing.routes import ...`) | Use the feature's public surface (its `__init__.py`) |
| `shared/utils.py` or `shared/helpers.py` | Junk drawer |
| Multiple Blueprints registered ad-hoc outside `create_app` | All registration lives in the factory |
| Global Flask context manipulation outside requests | Use `app.app_context()` deliberately, scoped |
| Sync calls to slow services inside request handlers without timeouts | Set per-request timeouts; consider async (FastAPI) for IO-heavy apps |

---

## Review checklist

```
Structure
  □ create_app() factory in myapp/__init__.py
  □ Extensions defined once in myapp/extensions.py
  □ Per-feature folders contain blueprint + routes + service + schemas + models
  □ shared/ contains only code used by 3+ features

Boundary
  □ Every route validates input with Marshmallow / Pydantic
  □ Routes never touch SQLAlchemy session directly
  □ Responses serialized through a schema (no raw models)

Service layer
  □ Services orchestrate transactions
  □ Repositories own DB access per feature
  □ Services raise AppError subclasses, not return JSON

Error handling
  □ AppError hierarchy in shared/errors.py
  □ register_error_handlers() called in the factory
  □ No ad-hoc 4xx responses scattered through view functions

Cross-feature
  □ Imports through feature's __init__.py (Blueprint + public service)
  □ Identity / auth treated as foundational

Configuration
  □ Config classes for dev / prod / test
  □ Required env vars resolved at config-class load time
```
