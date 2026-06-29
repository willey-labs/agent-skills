# Anti-slop (SL)

Slop is text that sounds like content but carries none. It comes from training that rewarded
longer, more-hedged, more-formatted output. Each rule below names a pattern, shows it, and gives
the fix. Apply to every document; do not apply to debugging output or code.

A document passes when every sentence earns its place: remove it and the reader loses real
information. If removing a sentence loses nothing, the sentence was slop.

---

## SL-001 — No hedging on things that aren't uncertain

Cut `may`, `might`, `could`, `generally`, `typically`, `potentially`, `it is recommended` when the
fact is definite. Hedge only when you're actually unsure — and then say so plainly ("I'm not sure").

- Bad: *The script may potentially update the database, which is generally recommended.*
- Good: *The script updates the database.*

## SL-002 — No hype words or empty adjectives

Banned: leverage, utilize, robust, seamless, scalable, holistic, cutting-edge, game-changing,
revolutionize, powerful, rich, vibrant. Either say the concrete thing or delete the word.

- Bad: *a robust, seamless solution that leverages a scalable architecture*
- Good: *handles 10k requests/sec; one config file; no restart on deploy* (or just name what it does)

## SL-003 — No throat-clearing

Don't announce what you're about to say. Say it.

- Bad: *To answer your question about the config, let's first take a look at…*
- Good: *(the config answer, directly)*

## SL-004 — No cheerleading or conversational filler

No "Let's dive in", "Great job", "Congratulations", "Happy coding", "Hope this helps". A document
is not a chat.

## SL-005 — Don't over-format

Default to prose. Use a heading, bold, or a list only when the content is genuinely a heading,
emphasis, or a list. Reflexive headers on a three-line answer, bold on every other phrase, and
emoji are slop. A real list (steps, options, fields) stays a list.

## SL-006 — Say each fact once

No restating the same point in different words within a section. No "summary" that repeats the body.
No padding to fill a section that has nothing more to say.

## SL-007 — Active voice, imperative, direct connectors

Prefer active voice and imperative verbs. Cut prepositional padding.

- Bad: *In order to facilitate the initialization of the cache, the function should be called.*
- Good: *Call it to initialize the cache.*

## SL-008 — No irrelevant contrastive negatives

Don't state what something is *not* unless the reader would otherwise assume it.

- Bad: *This endpoint returns the user. Note that it does not return the user's orders, posts,
  sessions, or payment methods.*
- Good: *Returns the user.*

## SL-009 — Don't explain the self-explanatory

Don't define a name that defines itself. `deleteUser` deletes a user; don't write a sentence saying
so. Spend words on what isn't obvious — edge cases, constraints, why.

## SL-010 — Don't invent structure for simple content

No "Phase 1 / Phase 2" or invented categories for a short linear process. No Intro–Body–Conclusion
scaffolding on a technical note. Match the structure to the content's real shape.

## SL-011 — No defensive disclaimers or fake nuance

Don't bolt safety warnings onto routine operations, and don't manufacture gray areas around binary
facts to look balanced. State the fact. Warn only about real, non-obvious risk.

## SL-012 — Don't narrate the document's own structure

Write about the subject, not about the document. Cut sentences describing how the page is laid out,
what it shares with sibling pages, or where to look next — "shared by every X; the per-X pages link
here instead of repeating it", "as noted above", "see the section below", "this page covers A, the
next covers B". The links and the layout already do that; saying it is plumbing the reader didn't
ask for. State the fact and let the structure carry itself.

---

## Not rules — deliberately dropped

These appear in popular "anti-slop" prompt configs and backfire. Don't adopt them:

- **Banning all pronouns.** "I/we/you" are fine and often clearer; forcing them out makes stilted
  prose. Drop them only in a pure formal spec where it reads better, not everywhere.
- **A fixed code-to-text ratio** (e.g. "70% must be code"). Unmeasurable and wrong for most docs;
  the right amount of code is whatever the doc needs — often, per SD-001, none.
- **Rejecting paragraphs / forcing everything into tables.** Prose is the default for explanation.
  Use a table when the data is tabular, not as a blanket rule.

Precision over dogma: a banned word in a quote, or a hedge on something genuinely uncertain, is
correct. These are defaults, not a word filter to apply blindly.
