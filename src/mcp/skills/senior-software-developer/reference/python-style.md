# Python Style Guide

---
**Language:** Python
**Use when:** Working with Python projects, modules, or scripts
---

## Naming Conventions

```python
# Module names: lowercase with underscores
# user_service.py

# Class names: PascalCase
class UserService:
    pass

# Function/method names: snake_case
def get_user_by_id(user_id: int) -> User:
    pass

# Constants: UPPER_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private methods/attributes: leading underscore
class User:
    def __init__(self):
        self._password_hash = None  # Private
    
    def _validate(self):  # Private method
        pass
```

## Type Hints (Required)

```python
from typing import Optional, Union, Callable
from collections.abc import Sequence

# Always use type hints for function signatures
def process_users(
    users: list[User],
    filter_fn: Optional[Callable[[User], bool]] = None,
    max_count: int = 100
) -> dict[str, Any]:
    """
    Process users with optional filtering.
    
    Args:
        users: List of users to process
        filter_fn: Optional function to filter users
        max_count: Maximum number of users to process
    
    Returns:
        Dictionary containing processed results
    """
    pass

# Use Optional for nullable types
def find_user(user_id: int) -> Optional[User]:
    pass

# Use Union for multiple possible types
def parse_input(value: Union[str, int]) -> str:
    pass

# Python 3.10+ modern syntax (preferred)
def process_items(items: list[str]) -> dict[str, int]:
    pass
```

## Project Structure

```
project/
├── pyproject.toml          # Modern Python packaging (use uv)
├── .python-version         # Python version for uv
├── uv.lock                 # Lock file from uv
├── .env.example           # Environment variable template
├── README.md
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── user.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── user_service.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   └── user_repository.py
│       └── utils/
│           ├── __init__.py
│           └── validators.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Pytest fixtures
│   ├── unit/
│   │   └── test_user_service.py
│   └── integration/
│       └── test_user_repository.py
└── .venv/                 # Virtual environment (created by uv)
```

## Modern Python Idioms

```python
# Use dataclasses for data containers
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class User:
    id: int
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    roles: list[str] = field(default_factory=list)

# Use pathlib for file paths (always)
from pathlib import Path

config_dir = Path(__file__).parent / "config"
config_file = config_dir / "settings.json"

with config_file.open() as f:
    data = f.read()

# Use context managers for resources
with open("file.txt") as f, db.transaction():
    data = f.read()
    db.save(data)

# Use comprehensions (but keep readable)
squares = [x**2 for x in range(10)]
user_map = {user.id: user for user in users}
unique_emails = {user.email for user in users}

# Generator expressions for memory efficiency
total = sum(user.balance for user in users)

# Walrus operator (Python 3.8+)
if (user := get_user(user_id)) is not None:
    process_user(user)

# Match statement (Python 3.10+)
match response.status:
    case 200:
        return response.json()
    case 404:
        raise NotFoundError()
    case _:
        raise UnexpectedError()
```

## Error Handling

```python
# Custom exception hierarchy
class ApplicationError(Exception):
    """Base exception for application errors"""
    pass

class ValidationError(ApplicationError):
    """Raised when validation fails"""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")

class NotFoundError(ApplicationError):
    """Resource not found"""
    pass

class UnauthorizedError(ApplicationError):
    """User not authorized"""
    pass

# Specific exception handling
try:
    result = risky_operation()
except FileNotFoundError:
    logger.error("Configuration file missing")
    raise
except ValidationError as e:
    logger.warning(f"Validation failed: {e}")
    return {"error": str(e)}, 400
except Exception:
    logger.exception("Unexpected error")
    raise
finally:
    cleanup()

# Context managers for cleanup
from contextlib import contextmanager

@contextmanager
def transaction(db):
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
```

## Dependency Injection

```python
# Parameter injection (simple)
def process_user(user_id: int, db: Database = get_default_db()) -> User:
    return db.query(User).get(user_id)

# Constructor injection (classes)
class UserService:
    def __init__(self, repository: UserRepository, logger: Logger):
        self.repository = repository
        self.logger = logger
    
    def get_user(self, user_id: int) -> User:
        return self.repository.find_by_id(user_id)
```

## Configuration with pyproject.toml

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "Project description"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "sqlalchemy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --cov=src --cov-report=term --cov-report=html"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Tools to Use

**Package Management:**
- `uv` - Modern, fast Python package manager
- Commands: `uv sync`, `uv add`, `uv run`

**Formatting:**
- `black` - Code formatter
- `ruff format` - Faster alternative

**Linting:**
- `ruff` - Fast linter (replaces flake8, isort, others)
- `pylint` - Advanced linting (optional)

**Type Checking:**
- `mypy` - Static type checker (required)

**Testing:**
- `pytest` - Test framework
- `pytest-cov` - Coverage plugin

## Quick Commands

```bash
# Setup with uv
uv venv                    # Create virtual environment
uv sync                    # Sync dependencies from pyproject.toml
uv add package             # Add a package

# Development
uv run pytest              # Run tests
uv run black .             # Format code
uv run ruff check .        # Lint code
uv run mypy .              # Type check

# Old style (if not using uv)
source .venv/bin/activate
pytest
black .
ruff check .
mypy .
```

## Best Practices

1. **Always use type hints** - No exceptions
2. **Use pathlib** - Never string manipulation for paths
3. **Prefer dataclasses** - Over plain dictionaries for data
4. **Use context managers** - For resource management
5. **Use uv** - Modern package management
6. **Enable strict mypy** - Catch type errors early
7. **Keep functions small** - < 20 lines ideally
8. **Docstrings for public APIs** - Google or NumPy style

## Anti-Patterns to Avoid

❌ **No type hints**
```python
def process_data(data):  # What type is data?
    return result
```

✅ **With type hints**
```python
def process_data(data: dict[str, Any]) -> ProcessedResult:
    return result
```

❌ **String path manipulation**
```python
path = os.path.join(base, "config", "settings.json")
```

✅ **Use pathlib**
```python
path = Path(base) / "config" / "settings.json"
```

❌ **Mutable default arguments**
```python
def add_item(item, items=[]):  # Dangerous!
    items.append(item)
```

✅ **Use None as default**
```python
def add_item(item, items: Optional[list] = None):
    if items is None:
        items = []
    items.append(item)
```

## Code Quality Standards

- Line length: 100 characters (black/ruff default)
- Import sorting: Automatic with ruff
- Type coverage: 100% for public APIs
- Test coverage: >80% overall, >90% for critical paths
- Docstrings: Required for all public functions/classes
