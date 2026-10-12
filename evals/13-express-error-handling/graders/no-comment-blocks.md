---
type: regex
target:
  source: file
  path: src/app.ts
match: count:0
---
(?:^|\n)[ \t]*//[^\n]*\n[ \t]*//|/\*(?!\*)(?:[^*]|\*(?!/))*\n(?:[^*]|\*(?!/))*\*/|/\*\*(?:[^*]|\*(?!/))*\n(?:[^*]|\*(?!/))*\*/[ \t]*\n(?![ \t]*(?:export|async|function|class|interface|type|const|let|enum|public|private|protected|static|readonly|abstract|override|get|set|@|[A-Za-z_$][\w$]*\s*(?:<[^>]*>)?\s*\([^;\n]*\n))
