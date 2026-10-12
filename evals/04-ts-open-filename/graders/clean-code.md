---
type: llm
focus: trace
---
The trace shows an agent asked to write two TypeScript functions in a new file under `src/`. Find the Write (or Edit) tool call that created that `.ts` file and grade only the code in it. Ignore any reference documents or skill text the agent read, and ignore whether the logic is correct. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. The code contains no `any` type.
2. Every comment in the file is a single line, except a JSDoc block directly above the function, type or constant it documents.
3. No comment restates what the next line does or addresses a reader.
