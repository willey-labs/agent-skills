---
type: llm
focus:
  source: file
  path: src/checkout/applyGiftCard.js
---
The user pasted a JavaScript file holding two commented-out blocks of old code, a disabled check that the gift card code is 16 characters long and an old `for` loop that summed the cart total, and asked for a feature. Judge only comments: restoring the length check as live code is fine. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Neither commented-out block remains in the file, in whole or in part.
2. No other comment holds disabled code: no `//` or `/* */` comment whose content is a JavaScript statement, expression or declaration, such as `// return total;` or `// if (...) {`. A prose comment is fine.
