# Senior Software Developer Skill

A modular, context-efficient skill for implementing production-ready code with senior-level judgment across Python, C#, Node.js, and TypeScript projects.

## Overview

This skill transforms the AI into a senior software engineer embedded in an agentic coding workflow. It emphasizes:

- **Assumption surfacing** - Never silently fill in ambiguous requirements
- **Simplicity enforcement** - Actively resist overcomplication
- **Scope discipline** - Touch only what needs touching
- **Confusion management** - Stop and clarify rather than guess
- **Push back when warranted** - Voice technical concerns
- **Production quality** - Deliver correct code on first attempt

## 🎯 What's New: Modular Structure

This skill has been redesigned for **context efficiency**. Instead of loading one large file with all languages, the skill now:

1. **Detects your project language** from file extensions and config files
2. **Loads only relevant references** (3 files per language vs. all content)
3. **Reduces token usage by ~70%** for language-specific work
4. **Works better with small context models** like GPT-3.5, Claude Haiku

### Language Detection

The skill automatically detects your language and loads appropriate references:

- **Python** (`.py`, `pyproject.toml`) → loads `python-style.md`, `python-testing.md`, `python-patterns.md`
- **C#** (`.cs`, `.csproj`, `.sln`) → loads `csharp-style.md`, `csharp-testing.md`, `csharp-patterns.md`
- **TypeScript** (`.ts`, `tsconfig.json`) → loads `typescript-style.md`, `typescript-testing.md`, `typescript-patterns.md`
- **Node.js** (`.js`, `package.json` with `type: "module"`) → loads `nodejs-style.md`, `nodejs-testing.md`, `nodejs-patterns.md`

## Quick Start

### Using the Skill

When working on a coding task:

1. **Activate the skill** in your AI assistant
2. **The skill detects your language** from your project files
3. **Provide requirements** - The skill will surface assumptions early
4. **Review inline plans** - For multi-step tasks, a plan is shown first
5. **Verify implementations** - Code is delivered test-first with verification steps

### File Structure

```
senior-software-developer/
├── SKILL.md                              # Main skill (streamlined, 400 lines)
├── README.md                             # This file
├── QUICK_REFERENCE.md                    # Cheat sheet for common patterns
│
├── reference/                            # Language-specific references
│   │
│   ├── python-style.md                   # Python style guide with uv
│   ├── python-testing.md                 # pytest, fixtures, mocking
│   ├── python-patterns.md                # SOLID in Python, Pythonic patterns
│   │
│   ├── csharp-style.md                   # C# style with nullable refs
│   ├── csharp-testing.md                 # xUnit, Moq, FluentAssertions
│   ├── csharp-patterns.md                # SOLID in C#, modern patterns
│   │
│   ├── typescript-style.md               # TypeScript strict mode patterns
│   ├── typescript-testing.md             # Jest patterns, mocking
│   ├── typescript-patterns.md            # Branded types, discriminated unions
│   │
│   ├── nodejs-style.md                   # Node.js async patterns, security
│   ├── nodejs-testing.md                 # Supertest, integration tests
│   └── nodejs-patterns.md                # Graceful shutdown, performance
│
└── scripts/                              # Utility scripts
    ├── README.md                         # Scripts documentation
    │
    ├── check_quality_python.py           # Python quality checks
    ├── check_quality_csharp.sh           # C# quality checks
    ├── check_quality_typescript.sh       # TypeScript quality checks
    ├── check_quality_nodejs.sh           # Node.js quality checks
    │
    ├── check_quality.py                  # Universal quality checker (legacy)
    ├── coverage_report.py                # Test coverage analyzer
    └── setup_dev_environment.sh          # Environment setup with uv
```

## Core Behaviors

### 1. Assumption Surfacing (CRITICAL)

Before implementing anything non-trivial, assumptions are explicitly stated:

```
ASSUMPTIONS I'M MAKING:
1. User authentication uses JWT tokens (not sessions) - affects caching strategy
2. Database queries can take up to 2s - need async/await throughout
3. API rate limits are 100 req/min - will implement exponential backoff
→ Correct me now or I'll proceed with these.
```

**Why:** The most common failure mode is making wrong assumptions and running with them unchecked.

### 2. Confusion Management (CRITICAL)

When encountering inconsistencies:

```
CONFUSION DETECTED:
File A expects User.email to be required
File B has email as nullable
File C accepts null emails

Which is the source of truth?
```

**Why:** Never silently pick one interpretation and hope it's right.

### 3. Simplicity Enforcement (HIGH)

Before finishing implementation:
- Can this be done in fewer lines without sacrificing clarity?
- Are these abstractions earning their complexity?
- Would a senior dev say "why didn't you just..."?

**Why:** Natural tendency is to overcomplicate. Actively resist it.

### 4. Scope Discipline (HIGH)

Touch only what you're asked to touch. Never:
- Remove comments you don't understand
- "Clean up" code orthogonal to the task
- Refactor adjacent systems as side effects
- Delete code that seems unused without approval

**Why:** Surgical precision, not unsolicited renovation.

### 5. Test-First Leverage

For non-trivial logic:
1. Write the test that defines success
2. Implement until test passes
3. Show both test and implementation

**Why:** Tests are your loop condition. Use them.

## Language-Specific Guides

Each language has three comprehensive reference files:

### Python (with uv package manager)

**Style Guide** (`python-style.md`):
- Modern Python with uv package manager
- Type hints with mypy
- Dataclasses and Pydantic
- pathlib for file operations
- pyproject.toml configuration

**Testing** (`python-testing.md`):
- pytest with fixtures and parametrized tests
- Mocking with unittest.mock
- Async testing with pytest-asyncio
- Factory pattern for test data
- Coverage with pytest-cov

**Patterns** (`python-patterns.md`):
- SOLID principles with ABC and Protocol
- Pythonic patterns (Context managers, match statements)
- Result types for error handling
- Performance patterns (N+1, caching with lru_cache)
- Anti-patterns to avoid

### C# (modern .NET 8+)

**Style Guide** (`csharp-style.md`):
- Microsoft naming conventions
- Nullable reference types
- Modern C# features (records, pattern matching, file-scoped namespaces)
- Dependency injection
- .editorconfig and Directory.Build.props

**Testing** (`csharp-testing.md`):
- xUnit with Theory and InlineData
- Mocking with Moq
- FluentAssertions for readable tests
- Integration tests with EF Core InMemoryDatabase
- Coverage with coverlet

**Patterns** (`csharp-patterns.md`):
- SOLID principles with interfaces
- Options pattern for configuration
- Result types for error handling
- Polly for retry logic
- IDisposable and IAsyncDisposable

### TypeScript (strict mode)

**Style Guide** (`typescript-style.md`):
- Strict TypeScript configuration
- Type system patterns (interfaces, utility types, branded types)
- Modern features (optional chaining, nullish coalescing, template literal types)
- tsconfig.json with strict mode
- ESLint and Prettier

**Testing** (`typescript-testing.md`):
- Jest with describe/it patterns
- Parametrized tests with test.each
- Mocking (functions, modules, timers)
- Integration tests with Supertest
- Snapshot testing

**Patterns** (`typescript-patterns.md`):
- SOLID principles in TypeScript
- Branded types for nominal typing
- Discriminated unions for state management
- Advanced types (conditional, mapped, template literal)
- Result types for error handling

### Node.js (ESM modules)

**Style Guide** (`nodejs-style.md`):
- package.json with type: "module"
- Environment validation with Zod
- Async patterns (Promise.all, AbortController)
- Graceful shutdown handling
- Security best practices (Helmet, rate limiting)

**Testing** (`nodejs-testing.md`):
- Supertest for API testing
- Integration tests with full API flows
- Database testing with testcontainers
- Testing streams
- Async testing patterns

**Patterns** (`nodejs-patterns.md`):
- Async/await patterns and error handling
- Graceful shutdown implementation
- Performance (worker threads, cluster, streams)
- Security (Zod validation, SQL injection prevention)
- Logging with Pino

## Utility Scripts

### Language-Specific Quality Checks

Each language has a dedicated quality check script:

**Python** (`check_quality_python.py`):
```bash
python3 scripts/check_quality_python.py
```
Runs: black, ruff, mypy, pytest with coverage

**C#** (`check_quality_csharp.sh`):
```bash
./scripts/check_quality_csharp.sh
```
Runs: dotnet format, dotnet build, dotnet test with coverage

**TypeScript** (`check_quality_typescript.sh`):
```bash
./scripts/check_quality_typescript.sh
```
Runs: tsc --noEmit, eslint, prettier, jest with coverage

**Node.js** (`check_quality_nodejs.sh`):
```bash
./scripts/check_quality_nodejs.sh
```
Runs: eslint, prettier, jest/vitest with coverage, npm audit

### Environment Setup with uv

The setup script now uses **uv** for modern Python development:

```bash
./scripts/setup_dev_environment.sh
```

**What it does:**

- **Python**: Uses uv for package management
  - Checks for existing `.venv` before creating
  - If `pyproject.toml` exists → uses `uv sync`
  - If `requirements.txt` exists → uses `uv pip install`
  - Installs dev tools (pytest, black, ruff, mypy)

- **C#**: Sets up .NET environment
  - Runs `dotnet restore`
  - Installs dotnet-format
  - Restores .NET tools

- **Node.js/TypeScript**: Sets up npm environment
  - Runs `npm install`
  - Installs dev dependencies
  - Sets up husky git hooks if available

- **Creates config files**:
  - `.gitignore` (with .venv/, node_modules/, bin/, obj/)
  - `.editorconfig` (consistent formatting across editors)

## Modern Python with uv

This skill now uses **uv** for Python development:

### Why uv?

- **Fast**: 10-100x faster than pip
- **Modern**: Works with pyproject.toml natively
- **Reliable**: Reproducible builds with lockfile
- **Complete**: Replaces pip, pip-tools, virtualenv

### Quick uv Commands

```bash
# Create virtual environment
uv venv

# Sync dependencies from pyproject.toml
uv sync

# Add a new dependency
uv add requests

# Add a dev dependency
uv add --dev pytest

# Install from requirements.txt (legacy)
uv pip install -r requirements.txt
```

### pyproject.toml Example

```toml
[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "fastapi>=0.104.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"
```

## Migration from Old Structure

If you're upgrading from the previous monolithic version:

### What Changed

1. **SKILL.md**: Reduced from 857 to ~400 lines
   - Removed duplicated language-specific examples
   - Added language detection section
   - Now references modular files instead of containing everything

2. **Reference files**: Split into language-specific files
   - **Before**: `language-style-guides.md` (871 lines for all languages)
   - **After**: `python-style.md` (350 lines), `csharp-style.md` (350 lines), etc.

3. **Python tooling**: Migrated from pip to uv
   - **Before**: `python3 -m venv`, `pip install`
   - **After**: `uv venv`, `uv sync`, `uv add`

4. **Quality scripts**: Created language-specific versions
   - **Before**: One `check_quality.py` trying to handle all languages
   - **After**: Dedicated scripts for each language with language-specific tools

### What Stayed the Same

- Core behaviors (assumption surfacing, confusion management, etc.)
- Code quality standards
- Test-first approach
- All previous functionality is preserved

### Migration Steps

1. **No action needed** - The skill automatically detects your language
2. **For Python projects**: Consider migrating to uv and pyproject.toml
3. **Use language-specific scripts**: `check_quality_python.py` instead of `check_quality.py`

## Contributing

To add support for a new language:

1. Create three reference files:
   - `reference/{language}-style.md` - Style guide
   - `reference/{language}-testing.md` - Testing patterns
   - `reference/{language}-patterns.md` - Design patterns

2. Add detection logic to `SKILL.md`:
   ```markdown
   ### {Language} Detection
   **Indicators:** .ext files, config.json
   **Load these references:** {language}-style.md, {language}-testing.md, {language}-patterns.md
   **Key tools:** tool1, tool2, tool3
   ```

3. Create quality check script:
   - `scripts/check_quality_{language}.sh`

4. Update `setup_dev_environment.sh` to detect and configure the language

## License

See `LICENSE.txt` for details.

## Support

For issues or questions:
- Review `SKILL.md` for the main operational guidelines
- Check language-specific reference files for detailed patterns
- Use `QUICK_REFERENCE.md` for common scenarios
- Run quality check scripts to validate your setup
