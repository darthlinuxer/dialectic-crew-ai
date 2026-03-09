# Senior Software Developer - Quick Reference

## Using the Modular Structure

### Language Detection

The skill automatically detects your language and loads only relevant files:

| Language   | Indicators                              | Files Loaded                                                        |
|------------|----------------------------------------|---------------------------------------------------------------------|
| Python     | `.py`, `pyproject.toml`, `requirements.txt` | `python-style.md`, `python-testing.md`, `python-patterns.md`       |
| C#         | `.cs`, `.csproj`, `.sln`               | `csharp-style.md`, `csharp-testing.md`, `csharp-patterns.md`       |
| TypeScript | `.ts`, `tsconfig.json`                 | `typescript-style.md`, `typescript-testing.md`, `typescript-patterns.md` |
| Node.js    | `.js`, `package.json` (ESM)            | `nodejs-style.md`, `nodejs-testing.md`, `nodejs-patterns.md`       |

### Token Savings

**Before (Monolithic):**
- Loading SKILL.md (857 lines) + language-style-guides.md (871 lines) = ~3000 tokens

**After (Modular):**
- Loading SKILL.md (400 lines) + 3 language files (~1200 lines) = ~1600 tokens
- **~70% reduction** for language-specific work

## Decision Trees

### Should I surface assumptions?

```
Is the implementation non-trivial? ────No───→ Just implement it
         │
        Yes
         │
         ↓
Are there ambiguities? ────No───→ Just implement it
         │
        Yes
         │
         ↓
SURFACE ASSUMPTIONS
Format them clearly
List concrete impacts
Ask for correction
```

### Should I stop for clarification?

```
Do I encounter inconsistency? ────No───→ Continue
         │
        Yes
         │
         ↓
Can I resolve it myself? ────Yes───→ Document decision
         │                              Continue
         No
         │
         ↓
STOP AND CLARIFY
Name the confusion
Present options/tradeoffs
Wait for resolution
```

### Should I push back?

```
Is proposed approach problematic? ────No───→ Implement as requested
         │
        Yes
         │
         ↓
Is it a security risk? ─────────────Yes───→ PUSH BACK (high priority)
         │
         No
         │
         ↓
Will it cause significant technical debt? ──Yes───→ PUSH BACK (medium priority)
         │
         No
         │
         ↓
Is it just a stylistic preference? ─────────Yes───→ Implement as requested
         │
         No
         │
         ↓
EVALUATE TRADEOFFS
Present alternatives
Explain impacts
Accept their decision
```

## Communication Templates

### Assumption Surfacing

```
ASSUMPTIONS I'M MAKING:
1. [assumption] — [concrete impact]
2. [assumption] — [concrete impact]
→ Correct me now or I'll proceed with these.
```

**Example:**
```
ASSUMPTIONS I'M MAKING:
1. Database uses UTC timezone — date comparisons will use UTC
2. JWT token in Authorization header — will parse Bearer format
3. Email is unique constraint in DB — skip duplicate checks in code
→ Correct me now or I'll proceed with these.
```

### Confusion Management

```
CONFUSION DETECTED:
[Specific inconsistency with examples]

Which is the source of truth? This affects:
- [Impact 1]
- [Impact 2]
```

**Example:**
```
CONFUSION DETECTED:
File A expects User.email to be required (string)
File B has email as optional (string | null)
File C accepts null emails without validation

Which is the source of truth? This affects:
- Validation logic in registration endpoint
- Database schema migration
```

### Push Back

```
CONCERN WITH PROPOSED APPROACH:
Requested: [What they asked for]

Problem: [Specific technical issue]
- [Concrete downside 1]
- [Concrete downside 2]

Alternative: [Better approach]
- [Benefit 1]
- [Benefit 2]

Tradeoff: [What alternative costs]

I recommend the alternative, but will implement your approach if you confirm.
```

**Example:**
```
CONCERN WITH PROPOSED APPROACH:
Requested: Store passwords in plain text

Problem: Massive security vulnerability
- Violates OWASP guidelines
- Regulatory non-compliance (GDPR, CCPA)
- Complete compromise if database leaked

Alternative: Use bcrypt for password hashing
- Industry standard security
- Minimal performance impact (~60ms per hash)
- No change to user experience

Tradeoff: Slightly more complex implementation (10 lines)

I strongly recommend bcrypt. Proceed with plain text?
```

### Inline Planning

```
PLAN:
1. [step] — [what it achieves]
2. [step] — [what it achieves]
3. [step] — [what it achieves]

Expected outcome: [success state]
Potential issues: [risks to watch]

→ Executing unless you redirect.
```

**Example:**
```
PLAN:
1. Add email field to User model — establishes data structure
2. Create database migration — adds email column with unique constraint
3. Update registration endpoint — validates email format and uniqueness
4. Add integration test — proves full registration flow works

Expected outcome: Users must provide unique email at registration
Potential issues: Existing users without emails need backfill migration

→ Executing unless you redirect.
```

### Change Summary

```
CHANGES MADE:
- [file]:[lines] — [what and why]

VERIFICATION STEPS:
- [how to verify]

POTENTIAL CONCERNS:
- [risks or things to verify]
```

**Example:**
```
CHANGES MADE:
- api/users.py:45-67 — Added email validation using regex
- tests/test_users.py:89-102 — Added tests for email validation edge cases

VERIFICATION STEPS:
- Run: pytest tests/test_users.py::test_email_validation -v
- Manual: POST /users with invalid email, expect 400 response

POTENTIAL CONCERNS:
- Regex allows "user@domain" without TLD (intentional for internal emails)
```

## Language-Specific Quick Guides

### Python (with uv)

**Setup:**
```bash
# Create .venv with uv
uv venv

# Sync from pyproject.toml
uv sync

# Add dependency
uv add fastapi

# Add dev dependency
uv add --dev pytest
```

**Common Commands:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests with coverage
pytest --cov=. --cov-report=html

# Format code
black .

# Lint
ruff check .

# Type check
mypy .

# Quality check all
python3 scripts/check_quality_python.py
```

**Key Patterns:**
- Type hints: `def func(x: int) -> str:`
- Dataclasses: `@dataclass` for data structures
- pathlib: `Path("file.txt").read_text()`
- Context managers: `with open(...) as f:`
- Match statements: Python 3.10+ pattern matching

**See:** `reference/python-style.md`, `python-testing.md`, `python-patterns.md`

### C# (modern .NET 8+)

**Setup:**
```bash
# Restore packages
dotnet restore

# Build
dotnet build

# Run tests with coverage
dotnet test --collect:"XPlat Code Coverage"
```

**Common Commands:**
```bash
# Format code
dotnet format

# Run specific test
dotnet test --filter "FullyQualifiedName~ClassName.MethodName"

# Quality check all
./scripts/check_quality_csharp.sh
```

**Key Patterns:**
- Nullable refs: `string?` vs `string`
- Record types: `public record User(int Id, string Email);`
- Pattern matching: `switch` expressions
- Async/await: `async Task<T>`
- File-scoped namespaces: `namespace MyApp;`

**See:** `reference/csharp-style.md`, `csharp-testing.md`, `csharp-patterns.md`

### TypeScript (strict mode)

**Setup:**
```bash
# Install dependencies
npm install

# Run type check
npx tsc --noEmit

# Run tests with coverage
npm test -- --coverage
```

**Common Commands:**
```bash
# Lint
npm run lint

# Format
npx prettier --write "**/*.{ts,tsx}"

# Run specific test
npm test -- UserService.test.ts

# Quality check all
./scripts/check_quality_typescript.sh
```

**Key Patterns:**
- Strict types: `strict: true` in tsconfig
- Interfaces: `interface User { id: number; }`
- Utility types: `Partial<T>`, `Pick<T, K>`, `Omit<T, K>`
- Branded types: `type UserId = number & { __brand: 'UserId' }`
- Type guards: `function isUser(x: unknown): x is User`

**See:** `reference/typescript-style.md`, `typescript-testing.md`, `typescript-patterns.md`

### Node.js (ESM modules)

**Setup:**
```bash
# Install dependencies
npm install

# Run tests
npm test

# Security audit
npm audit
```

**Common Commands:**
```bash
# Run with debugging
node --inspect index.js

# Run with environment variables
NODE_ENV=production node index.js

# Quality check all
./scripts/check_quality_nodejs.sh
```

**Key Patterns:**
- ESM: `import/export` with `"type": "module"`
- Async/await: Always use for I/O operations
- Environment validation: Use Zod or similar
- Graceful shutdown: Handle SIGTERM/SIGINT
- Streams: For large data processing

**See:** `reference/nodejs-style.md`, `nodejs-testing.md`, `nodejs-patterns.md`

## Testing Quick Patterns

### Python (pytest)

```python
# Basic test
def test_user_creation():
    user = User(email="test@example.com")
    assert user.email == "test@example.com"

# Parametrized test
@pytest.mark.parametrize("email,valid", [
    ("test@example.com", True),
    ("invalid", False),
])
def test_email_validation(email, valid):
    assert validate_email(email) == valid

# Fixture
@pytest.fixture
def user():
    return User(email="test@example.com")

def test_with_fixture(user):
    assert user.email
```

### C# (xUnit)

```csharp
// Basic test
[Fact]
public void UserCreation_SetsEmail()
{
    var user = new User("test@example.com");
    Assert.Equal("test@example.com", user.Email);
}

// Parametrized test
[Theory]
[InlineData("test@example.com", true)]
[InlineData("invalid", false)]
public void EmailValidation(string email, bool expected)
{
    Assert.Equal(expected, ValidateEmail(email));
}

// Fixture
public class UserTests : IClassFixture<DatabaseFixture>
{
    private readonly DatabaseFixture _db;
    
    public UserTests(DatabaseFixture db) => _db = db;
}
```

### TypeScript/Node.js (Jest)

```typescript
// Basic test
describe('User', () => {
  it('should create user with email', () => {
    const user = new User('test@example.com');
    expect(user.email).toBe('test@example.com');
  });
});

// Parametrized test
test.each([
  ['test@example.com', true],
  ['invalid', false],
])('validates email %s as %s', (email, expected) => {
  expect(validateEmail(email)).toBe(expected);
});

// Mocking
const mockFn = jest.fn();
mockFn.mockReturnValue(42);
```

## Common Anti-Patterns to Avoid

### 1. God Object
❌ **Wrong:** One class doing everything
```python
class UserManager:
    def authenticate(self): ...
    def send_email(self): ...
    def generate_report(self): ...
    def process_payment(self): ...
```

✅ **Right:** Single responsibility
```python
class Authenticator: ...
class EmailService: ...
class ReportGenerator: ...
class PaymentProcessor: ...
```

### 2. Primitive Obsession
❌ **Wrong:** Using primitives everywhere
```typescript
function sendEmail(email: string, subject: string, body: string)
```

✅ **Right:** Use domain types
```typescript
type Email = string & { __brand: 'Email' };
interface EmailMessage {
  to: Email;
  subject: string;
  body: string;
}
function sendEmail(message: EmailMessage)
```

### 3. Magic Numbers
❌ **Wrong:** Unexplained constants
```csharp
if (user.Age > 18 && user.AccountBalance > 1000)
```

✅ **Right:** Named constants
```csharp
const int LEGAL_AGE = 18;
const decimal MINIMUM_BALANCE = 1000m;
if (user.Age > LEGAL_AGE && user.AccountBalance > MINIMUM_BALANCE)
```

## Script Quick Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup_dev_environment.sh` | Initial environment setup | `./scripts/setup_dev_environment.sh` |
| `check_quality_python.py` | Python quality checks | `python3 scripts/check_quality_python.py` |
| `check_quality_csharp.sh` | C# quality checks | `./scripts/check_quality_csharp.sh` |
| `check_quality_typescript.sh` | TypeScript quality checks | `./scripts/check_quality_typescript.sh` |
| `check_quality_nodejs.sh` | Node.js quality checks | `./scripts/check_quality_nodejs.sh` |

## Getting Started Checklist

- [ ] Activate the senior-software-developer skill
- [ ] Run `./scripts/setup_dev_environment.sh` to set up your environment
- [ ] For Python: Ensure uv is installed (`curl -LsSf  | sh`)
- [ ] Review the language-specific reference file for your language
- [ ] Run the appropriate quality check script for your project
- [ ] Read `SKILL.md` for full operational guidelines

## Reference File Locations

All reference files are in the `reference/` directory:

```
reference/
├── python-style.md          # Python with uv
├── python-testing.md        # pytest patterns
├── python-patterns.md       # Pythonic design patterns
├── csharp-style.md          # C# with nullable refs
├── csharp-testing.md        # xUnit patterns
├── csharp-patterns.md       # C# design patterns
├── typescript-style.md      # TypeScript strict mode
├── typescript-testing.md    # Jest patterns
├── typescript-patterns.md   # TypeScript type patterns
├── nodejs-style.md          # Node.js async patterns
├── nodejs-testing.md        # Supertest patterns
└── nodejs-patterns.md       # Node.js runtime patterns
```

Each file is ~350-500 lines focused on one language and one topic.
