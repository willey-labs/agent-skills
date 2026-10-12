---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [php, write, laravel]
---
In our Laravel 11 app, add creating blog posts: write the form request `app/Http/Requests/StorePostRequest.php` and the `store` action of `app/Http/Controllers/PostController.php` (the controller doesn't exist yet).

Validation: `title` is required, at most 120 characters; `body` is required; `tags` is an optional array of at most 5 strings, each at most 30 characters; `publish_at` is an optional date that must be in the future. Any logged-in user may create posts (the route is already behind `auth`).

Each post gets a slug made from its title that's unique across posts: if `my-title` is taken, use `my-title-2`, then `my-title-3`, and so on. The `Post` model already exists with `title`, `slug`, `body`, `tags` (cast to array), `publish_at` and `user_id` fillable; set `user_id` to the current user. Respond `201` with the created post as JSON.
