---
type: llm
focus:
  source: file
  path: src/checkout/applyGiftCard.js
---
The file applies a gift card to a checkout cart. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (malformed codes, a cart with no eligible items, how a failed `recordRedemption` call is handled) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The code is trimmed and uppercased before `fetchGiftCard` is called with it, and a card that is not found or has expired still throws.
2. The most the card can cover is the total (`priceCents` × `quantity`) of the items whose `isGiftCard` is not true; items with `isGiftCard: true` do not count toward it.
3. The amount applied is the smaller of the card's `balanceCents` and that eligible total.
4. `amountDueCents` is the full cart total, gift-card items included, minus the amount applied.
5. `remainingBalanceCents` is the card's balance minus the amount applied, and `recordRedemption` is still called with the card's code and the amount applied.
6. The file holds only JavaScript: no markdown code fence (```) or other non-code text, so it would parse.
