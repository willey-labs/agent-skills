---
type: llm
focus:
  source: file
  path: app/login/login-view-model.ts
---
The file is a NativeScript view model for a login page. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (the wording of messages, trimming whitespace, clearing `formError` on a new submit, double submits while busy) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The class extends `Observable`, and the values it changes itself (`emailError`, `passwordError`, `formError`, `isBusy`) notify the UI: through `set(...)`, `notifyPropertyChange`, or setters that raise a property-change event. Plain field assignments that never notify fail this claim.
2. An empty email gives a required message and an email without text on both sides of an `@` gives an invalid-email message; an empty password gives a required message and one shorter than 8 characters gives a too-short message; a field that passes has its message cleared.
3. When validation fails, `submit()` does not call `login`.
4. When validation passes, `isBusy` becomes true before `login(email, password)` is called on the auth service received through the constructor, and success navigates to `home/home-page` (for example with `Frame.topmost().navigate`).
5. When `login` rejects, `formError` shows the error's message and there is no navigation; `isBusy` returns to false after both success and failure.
6. `AuthService` is declared as an interface with `login(email: string, password: string): Promise<void>`, and the class receives it through its constructor instead of creating it.
