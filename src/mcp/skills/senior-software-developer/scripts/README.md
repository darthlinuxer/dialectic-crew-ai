# Senior Software Developer Scripts

Utility scripts to support senior-level development workflow across Python, C#, Node.js, and TypeScript projects.

**Part of:** [senior-software-developer](../SKILL.md) skill  
**Referenced by:** [verification-before-completion](../../verification-before-completion/SKILL.md) skill

## Purpose

These scripts automate code quality checks and provide verification evidence for:
- Pre-commit quality gates
- Code review preparation
- CI/CD pipeline integration
- Verification before claiming completion (per **verification-before-completion** skill)

They implement the quality standards defined in:
- `../reference/python-style.md` and `python-patterns.md`
- `../reference/csharp-style.md` and `csharp-patterns.md`
- `../reference/typescript-style.md` and `typescript-patterns.md`
- `../reference/nodejs-style.md` and `nodejs-patterns.md`

## Available Scripts

### 1. `check_quality.py` - Code Quality Checker

Runs comprehensive code quality checks across your project.

**What it checks:**

**Python:**
- `black` - Code formatting
- `isort` - Import sorting
- `flake8` - Linting
- `mypy` - Type checking
- `pylint` - Advanced linting
- `pytest` - Tests with coverage

**C#:**
- `dotnet format` - Code formatting
- `dotnet build` - Build with warnings as errors
- `dotnet test` - Tests with coverage

**TypeScript/Node.js:**
- `eslint` - Linting
- `prettier` - Code formatting
- `tsc` - TypeScript type checking
- `jest` - Tests with coverage

**Usage:**
```bash
# Run from project root
python3 scripts/check_quality.py

# Or make it executable
chmod +x scripts/check_quality.py
./scripts/check_quality.py
```

**Output:**
- ✓ PASS / ✗ FAIL for each tool
- Error details for failed checks
- Summary of passed/failed checks

**Exit codes:**
- 0: All checks passed
- 1: One or more checks failed

**Perfect for:**
- Pre-commit verification
- CI/CD pipelines
- Code review preparation

---

### 2. `coverage_report.py` - Test Coverage Analyzer

Generates detailed test coverage reports with gap analysis.

**Features:**
- Runs coverage for Python (pytest), C# (coverlet), TypeScript/JavaScript (jest)
- Identifies files with low coverage
- Provides recommendations for improvement
- Generates HTML reports (language-specific)

**Usage:**
```bash
python3 scripts/coverage_report.py
```

**Output:**
- Overall coverage percentages (line, branch, function, statement)
- Per-file coverage breakdown
- List of files below 80% coverage
- Status rating (Excellent/Good/Acceptable/Needs Improvement)
- Actionable recommendations

**Coverage targets:**
- Critical business logic: 90-100%
- Service layer: 80-90%
- Controllers/APIs: 70-80%
- Utility functions: 80-90%

**Perfect for:**
- Identifying testing gaps
- Prioritizing test writing efforts
- Coverage tracking over time

---

### 3. `setup_dev_environment.sh` - Development Environment Setup

Automated setup of development environment with all necessary tools.

**What it does:**

**Python:**
- Creates virtual environment (`venv/`)
- Installs dependencies from `requirements.txt`
- Installs dev tools (pytest, black, flake8, mypy, pylint)
- Sets up pre-commit hooks

**C#:**
- Restores NuGet packages
- Installs .NET tools
- Installs/updates `dotnet-format`

**Node.js/TypeScript:**
- Installs npm packages
- Installs dev dependencies (TypeScript, ESLint, Prettier, Jest)
- Sets up Husky git hooks (if configured)

**All Projects:**
- Creates `.gitignore` (if missing)
- Creates `.editorconfig` (if missing)

**Usage:**
```bash
# Make executable
chmod +x scripts/setup_dev_environment.sh

# Run from project root
./scripts/setup_dev_environment.sh
```

**Perfect for:**
- New developer onboarding
- Fresh project setup
- Ensuring consistent tooling across team

---

## Installation

### Prerequisites

**Python projects:**
```bash
pip install pytest pytest-cov black isort flake8 mypy pylint pre-commit
```

**C# projects:**
```bash
dotnet tool install -g dotnet-format
```

**Node.js/TypeScript projects:**
```bash
npm install --save-dev \
  typescript \
  @typescript-eslint/eslint-plugin \
  @typescript-eslint/parser \
  eslint \
  prettier \
  jest \
  @types/jest \
  @types/node
```

### Quick Setup

Copy the scripts to your project:

```bash
# Create scripts directory
mkdir -p scripts

# Copy from senior-software-developer skill
cp /path/to/senior-software-developer/scripts/* scripts/

# Make shell scripts executable
chmod +x scripts/*.sh
```

---

## Integration Examples

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Code Quality
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest black flake8 mypy
      
      - name: Run quality checks
        run: python3 scripts/check_quality.py
      
      - name: Check coverage
        run: python3 scripts/coverage_report.py
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running quality checks..."
python3 scripts/check_quality.py
if [ $? -ne 0 ]; then
    echo "❌ Quality checks failed. Fix issues before committing."
    exit 1
fi
echo "✓ Quality checks passed"
```

### Makefile Integration

```makefile
.PHONY: quality coverage setup

quality:
	python3 scripts/check_quality.py

coverage:
	python3 scripts/coverage_report.py

setup:
	./scripts/setup_dev_environment.sh
```

---

## Configuration Files

### Python - `pyproject.toml`

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --cov=src --cov-report=term --cov-report=html"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### TypeScript - `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### ESLint - `.eslintrc.js`

```javascript
module.exports = {
  parser: '@typescript-eslint/parser',
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  rules: {
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn',
  },
};
```

### C# - `.editorconfig`

```ini
[*.cs]
# Naming conventions
dotnet_naming_rule.interfaces_should_be_prefixed_with_i.severity = warning
dotnet_naming_rule.interfaces_should_be_prefixed_with_i.symbols = interface
dotnet_naming_rule.interfaces_should_be_prefixed_with_i.style = begins_with_i

# Code style
csharp_prefer_braces = true:warning
csharp_using_directive_placement = outside_namespace:warning
```

---

## Troubleshooting

### "Tool not found" errors

**Python:**
```bash
source venv/bin/activate
pip install pytest black flake8 mypy pylint
```

**C#:**
```bash
dotnet tool restore
dotnet tool install -g dotnet-format
```

**Node.js:**
```bash
npm install
```

### Permission denied

```bash
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### Coverage files not generated

Make sure test runner plugins are installed:
- Python: `pip install pytest-cov`
- C#: Add `<PackageReference Include="coverlet.msbuild" Version="6.0.0" />`
- Node.js: `npm install --save-dev jest`

---

## Best Practices

1. **Run quality checks before committing**
   - Catches issues early
   - Maintains code quality
   - Prevents CI failures

2. **Monitor coverage trends**
   - Run coverage reports regularly
   - Track improvement over time
   - Focus on high-risk areas

3. **Automate environment setup**
   - Use `setup_dev_environment.sh` for new devs
   - Document any manual steps required
   - Keep tool versions consistent

4. **Integrate with CI/CD**
   - Fail builds on quality issues
   - Enforce minimum coverage thresholds
   - Generate reports as artifacts

---

## Contributing

To add support for additional tools or languages:

1. Edit `check_quality.py` to add new checker methods
2. Update `coverage_report.py` for coverage analysis
3. Modify `setup_dev_environment.sh` for environment setup
4. Update this README with new tool documentation

---

## License

These scripts are provided as part of the senior-software-developer skill for use in your projects.
