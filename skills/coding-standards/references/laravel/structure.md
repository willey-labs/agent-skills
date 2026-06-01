# Laravel — Structure

## Builds on `common/structure.md`

Laravel is the one **exception** to "name the top folders by business." Its routing, queues, scheduling,
broadcasting, and `make:*` generators all expect the stock skeleton (`app/Http/Controllers/`,
`app/Models/`, `app/Services/`, …). So keep the stock skeleton at the top of `app/` — don't fight it with
`app/<Business>/`. Apply the business → feature → sub-feature → unit model from `common/structure.md` *inside*
those stock folders. The rest of `common/` (front door, Rule of Three, no junk drawers, one job per file)
applies unchanged.

## Outer shell

Once a capability gains supporting files, group it with a subfolder *within* its stock parent — and repeat
the same business subfolder across every layer:

```
app/Http/Controllers/<Business>/<Business>Controller.php
app/Http/Requests/<Business>/<Action>Request.php
app/Models/<Business>/<Entity>.php
app/Services/<Business>/                 ← the real domain logic
  <Feature>/                             ← sub-feature, earned (3+ files)
    <Feature>Service.php
    <Action>.php
    <Forms>/                             ← variants: interface + one file per form
```

(Laravel 11+ ships only `AppServiceProvider`; middleware, exceptions, and routing live in
`bootstrap/app.php`, not in stock provider classes.)

## Naming (PSR-4)

- **Folders are namespaces → `PascalCase`**: `app/Services/<Business>/`, never lowercase `<business>/`.
  The folder name is part of the class's namespace.
- **Files → `PascalCase.php`** matching the class inside.
- Models are nouns (`<Entity>.php`), action classes are verbs (`<Verb><Entity>.php`), `<Action>Request.php`,
  `<Entity>Resource.php`.

## Front door

Laravel has no `index` file. A folder's public surface is its **public service / action class** — callers
depend on that, not on its siblings. For swappable variants, the **interface** is the front door and the
implementation is bound in `AppServiceProvider`.

## Laravel specifics

- **Controllers are thin** — type-hint a Form Request to validate, type-hint a service (the container
  injects it), call it, return a Resource. No DB queries, business rules, or job dispatch in a controller;
  if a method runs past ~5 lines, move the body into the service.

- **Services own use cases** — one verb-named method per business action, or one invokable Action class per
  use case (pick one style, stay consistent). Past ~10 methods a service is a god class — split into Actions.

- **Validation → Form Requests** at the boundary (`rules()` + `authorize()`), never inline
  `$request->validate()` in a controller.

- **Responses → API Resources** — never return an Eloquent model straight from a controller; shape it
  through a Resource.

- **Eloquent is the allowed hybrid (`common/objects-and-data.md` OD-005).** Put behavior *on* the model when
  it's about the model's own data (`$<entity>->total()`, `$<entity>->cancel($reason)`, query scopes). Put it in a
  **service** when it coordinates multiple models or external systems (charge payment, send mail, dispatch
  jobs). The model must not become a god class owning cross-cutting workflows.

- **No repository wrapping a single Eloquent model** — Eloquent already is the data layer; a
  `find`/`save`/`delete` repository over one model adds nothing.
