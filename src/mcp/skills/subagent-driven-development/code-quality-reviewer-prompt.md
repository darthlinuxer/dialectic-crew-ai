# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

```
Task tool (superpowers:code-reviewer):
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: [from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan-file]
  BASE_SHA: [commit before task]
  HEAD_SHA: [current commit]
  DESCRIPTION: [task summary]

  ## Language-Specific Quality Criteria

  **C# Quality Checks:**
  - Proper async/await usage (no `.Result`, `.Wait()`, or blocking)
  - Nullable reference types handled correctly
  - IDisposable implemented and used correctly
  - LINQ usage appropriate (not overused)
  - Exceptions are specific, not generic
  - Dependency injection follows project patterns

  **Python Quality Checks:**
  - Type hints present and accurate (if project uses them)
  - PEP 8 compliant (naming, structure)
  - Context managers used for resources
  - List comprehensions readable (not overly complex)
  - Proper exception handling (specific exceptions)
  - No mutable default arguments

  **TypeScript/Node.js Quality Checks:**
  - Type safety (minimal/justified use of `any`)
  - Proper async/await (no unhandled promises)
  - Error handling present
  - No type assertions unless necessary (`as` keyword)
  - Immutability where appropriate
  - Follows project's ESLint/Prettier rules

  **Universal Quality Checks (All Languages):**
  - Names match what things DO, not HOW they work
  - No magic numbers (extract to named constants)
  - Functions/methods do one thing
  - No premature optimization or over-engineering (YAGNI)
  - Tests verify real behavior (see [testing-anti-patterns.md](../test-driven-development/testing-anti-patterns.md))
  - No test-only methods in production code
  - Evidence provided for all claims (see @verification-before-completion)
```

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment
