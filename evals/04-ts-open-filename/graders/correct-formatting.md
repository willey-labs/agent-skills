---
type: llm
focus: trace
---
The trace shows an agent asked to write two TypeScript functions in a new file under `src/`. Find the Write (or Edit) tool call that created that `.ts` file and grade only the code in it. Ignore any reference documents or skill text the agent read, and ignore comments and style. Behaviour the task did not specify (negative amounts, non-integer input, invalid dates) does not affect the verdict. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. A Write call created a `.ts` file under `src/`.
2. The money function turns an integer number of cents into a dollar string with a `$` sign, thousands separators and exactly two decimals: 123450 becomes `$1,234.50` and 5 becomes `$0.05`.
3. The date function returns `YYYY-MM-DD` with zero-padded month and day, and reads year, month and day all in UTC or all in local time.
