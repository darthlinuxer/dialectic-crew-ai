# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent.

```
Task tool (general-purpose):
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description

    [FULL TEXT of task from plan - paste it here, don't make subagent read file]

    ## Context

    [Scene-setting: where this fits, dependencies, architectural context]

    ## Before You Begin

    If you have questions about:
    - The requirements or acceptance criteria
    - The approach or implementation strategy
    - Dependencies or assumptions
    - Anything unclear in the task description

    **Ask them now.** Raise any concerns before starting work.

    ## Your Job

    Once you're clear on requirements:
    1. Implement exactly what the task specifies
    2. Write tests (following TDD if task says to)
    3. Verify implementation works
    4. Commit your work
    5. Self-review (see below)
    6. Report back

    Work from: [directory]

    ## Language-Specific Guidelines

    **C#:**
    - Use xUnit/NUnit/MSTest (match project convention)
    - Run `dotnet test` to verify tests
    - Run `dotnet build` to verify compilation
    - Follow nullable reference type rules if enabled
    - Use async/await properly (no `.Result` or `.Wait()`)

    **Python:**
    - Use pytest (or unittest if project uses it)
    - Run `pytest path/to/test.py -v` to verify
    - Check type hints with mypy if project uses them
    - Follow PEP 8 style guidelines

    **TypeScript/Node.js:**
    - Use Jest/Vitest (match project convention)
    - Run `npm test` or test command to verify
    - Run `npm run build` or `tsc --noEmit` to verify compilation
    - Ensure type safety (no `any` unless justified)
    - Use proper async/await patterns

    **All Languages:**
    - Follow @test-driven-development principles
    - Avoid [testing-anti-patterns.md](../test-driven-development/testing-anti-patterns.md) (especially testing mock behavior)
    - Use @verification-before-completion before claiming success

    **While you work:** If you encounter something unexpected or unclear, **ask questions**.
    It's always OK to pause and clarify. Don't guess or make assumptions.

    ## Before Reporting Back: Self-Review

    Review your work with fresh eyes. Ask yourself:

    **Completeness:**
    - Did I fully implement everything in the spec?
    - Did I miss any requirements?
    - Are there edge cases I didn't handle?

    **Quality:**
    - Is this my best work?
    - Are names clear and accurate (match what things do, not how they work)?
    - Is the code clean and maintainable?

    **Discipline:**
    - Did I avoid overbuilding (YAGNI)?
    - Did I only build what was requested?
    - Did I follow existing patterns in the codebase?

    **Testing:**
    - Do tests actually verify behavior (not just mock behavior)?
    - Did I follow TDD if required?
    - Are tests comprehensive?
    - Did I avoid testing mock behavior? (Anti-Pattern 1 in [testing-anti-patterns.md](../test-driven-development/testing-anti-patterns.md))
    - Did I avoid adding test-only methods to production classes? (Anti-Pattern 2)

    **Verification (CRITICAL - see @verification-before-completion):**
    - Did I run the test command and verify 0 failures?
    - For compiled languages (C#/TypeScript): Did I run build and verify it compiles?
    - Did I verify with fresh command output (not assumptions)?
    - Can I provide evidence for every claim I'm about to make?

    If you find issues during self-review, fix them now before reporting.

    ## Report Format

    When done, report:
    - What you implemented
    - What you tested and **evidence** (command output showing 0 failures)
    - For C#/TypeScript: Build verification **evidence** (command output showing successful compilation)
    - Files changed
    - Self-review findings (if any issues found and fixed)
    - Any issues or concerns

    **MANDATORY:** Follow @verification-before-completion - provide fresh command output as evidence.
    NO claims without verification evidence. "Should work" or "looks correct" is NOT acceptable.
```
