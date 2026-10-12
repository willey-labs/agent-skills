---
type: llm
focus:
  source: file
  path: app/Http/Controllers/PostController.php
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `$tmp`, `$res`, `$val`, `$cnt`, `$req`, and no single-letter names except a loop counter used only inside its loop.
2. No method body is longer than 25 lines.
3. Nothing is more elaborate than creating one post needs: no repository wrapping the `Post` model, no slug-strategy interface, Factory, or event/listener chain. A service or action class for creating the post, and an API Resource, are fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments (`/** */` docblocks). Apart from doc comments directly above the declaration they document, no comment runs past one line.
