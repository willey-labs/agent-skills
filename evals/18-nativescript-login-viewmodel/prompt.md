---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, nativescript]
---
In our NativeScript app (core flavour, TypeScript), write the login page's view model, `app/login/login-view-model.ts`.

It's a class extending `Observable` from `@nativescript/core`. The XML binds two-way to `email` and `password`, shows `emailError`, `passwordError` and `formError` under the fields, and disables the button while `isBusy` is true.

- Email is required and must look like an address: something, then `@`, then something.
- Password is required and must be at least 8 characters.
- `submit()` validates and shows the messages; if anything is invalid it stops there.
- Otherwise it sets `isBusy`, calls `login(email, password)` on the auth service passed to the constructor, and on success navigates to `home/home-page`. If login fails, it shows the error's message in `formError`. `isBusy` goes back to false either way.

Keep it all in that one file, including an `AuthService` interface with `login(email: string, password: string): Promise<void>`.
