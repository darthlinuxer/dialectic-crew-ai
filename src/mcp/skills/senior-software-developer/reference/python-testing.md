# Python Testing Guide

---
**Language:** Python
**Test Framework:** pytest (recommended), unittest
**Coverage Tool:** pytest-cov, coverage.py
---

## Test-Driven Development (TDD) Workflow

### Red-Green-Refactor Cycle

```
1. RED: Write a failing test
   ↓
2. GREEN: Write minimal code to pass
   ↓
3. REFACTOR: Improve code without breaking test
   ↓
4. Repeat
```

### Example: User Registration with TDD

**Step 1: Write the test (RED)**
```python
# tests/test_user_service.py
import pytest
from services.user_service import UserService
from models.user import User

def test_register_user_with_valid_data():
    # Arrange
    service = UserService()
    email = "test@example.com"
    password = "secure_password123"
    
    # Act
    result = service.register(email, password)
    
    # Assert
    assert result.success is True
    assert result.user.email == email
    assert result.user.password != password  # Should be hashed
    assert len(result.user.id) > 0

# Run: pytest tests/test_user_service.py
# Expected: FAIL - UserService.register() doesn't exist
```

**Step 2: Minimal implementation (GREEN)**
```python
# services/user_service.py
from dataclasses import dataclass
from models.user import User
import hashlib
import uuid

@dataclass
class RegistrationResult:
    success: bool
    user: User

class UserService:
    def register(self, email: str, password: str) -> RegistrationResult:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=hashed_password
        )
        return RegistrationResult(success=True, user=user)

# Run: pytest tests/test_user_service.py
# Expected: PASS
```

**Step 3: Refactor (REFACTOR)**
```python
# Extract password hashing to dedicated service
class PasswordHasher:
    def hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

class UserService:
    def __init__(self, hasher: PasswordHasher | None = None):
        self.hasher = hasher or PasswordHasher()
    
    def register(self, email: str, password: str) -> RegistrationResult:
        hashed_password = self.hasher.hash(password)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=hashed_password
        )
        return RegistrationResult(success=True, user=user)

# Run: pytest tests/test_user_service.py
# Expected: Still PASS
```

## Project Structure

```
project/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── models/
│   │   └── user.py
│   ├── services/
│   │   └── user_service.py
│   └── repositories/
│       └── user_repository.py
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures
    ├── unit/
    │   ├── test_user_service.py
    │   └── test_validators.py
    └── integration/
        └── test_user_repository.py
```

## pytest Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--showlocals",
    "-ra",  # Show extra test summary info
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-branch",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Unit Tests (70% of tests)

### Basic Structure
```python
# tests/unit/test_calculator.py
import pytest
from src.calculator import Calculator

class TestCalculator:
    def setup_method(self):
        """Run before each test method"""
        self.calc = Calculator()
    
    def test_add_positive_numbers(self):
        # Arrange (setup in setup_method)
        # Act
        result = self.calc.add(2, 3)
        # Assert
        assert result == 5
    
    def test_add_negative_numbers(self):
        result = self.calc.add(-2, -3)
        assert result == -5
    
    def test_divide_by_zero_raises_error(self):
        with pytest.raises(ZeroDivisionError):
            self.calc.divide(10, 0)
```

### Fixtures for Reusable Test Data

```python
# tests/conftest.py
import pytest
from src.database import Database
from src.models.user import User

@pytest.fixture
def db():
    """Provides a clean in-memory database for each test"""
    database = Database(':memory:')
    database.create_tables()
    yield database
    database.close()

@pytest.fixture
def sample_user() -> User:
    """Provides a sample user for tests"""
    return User(
        id="123",
        email="test@example.com",
        name="Test User"
    )

@pytest.fixture
def user_service(db):
    """Provides UserService with test database"""
    from src.services.user_service import UserService
    return UserService(database=db)

# Usage in tests
def test_save_user(db, sample_user):
    db.save(sample_user)
    retrieved = db.find_by_email(sample_user.email)
    assert retrieved.name == sample_user.name
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("age,expected", [
    (17, False),  # Below minimum
    (18, True),   # Minimum
    (19, True),   # Above minimum
    (119, True),  # Below maximum
    (120, True),  # Maximum
    (121, False), # Above maximum
])
def test_age_validation(age, expected):
    validator = AgeValidator(min_age=18, max_age=120)
    assert validator.is_valid(age) == expected

@pytest.mark.parametrize("email,is_valid", [
    ("test@example.com", True),
    ("invalid.email", False),
    ("@example.com", False),
    ("test@", False),
    ("", False),
    (None, False),
])
def test_email_validation(email, is_valid):
    validator = EmailValidator()
    assert validator.validate(email).is_valid == is_valid
```

## Mocking with unittest.mock

```python
from unittest.mock import Mock, patch, MagicMock, call
import requests

# Mock a function
def test_fetch_user_data():
    with patch('src.api.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {'id': 1, 'name': 'Alice'}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = fetch_user_data(1)
        
        assert result['name'] == 'Alice'
        mock_get.assert_called_once_with('

# Mock a class
def test_user_service_saves_to_repository():
    mock_repo = Mock()
    service = UserService(repository=mock_repo)
    
    user = User(id="123", email="test@example.com")
    service.save_user(user)
    
    mock_repo.save.assert_called_once_with(user)

# Mock with side effects
def test_retry_on_failure():
    mock_api = Mock()
    mock_api.call.side_effect = [
        ConnectionError("Failed"),
        ConnectionError("Failed"),
        {"status": "success"}
    ]
    
    result = retry_api_call(mock_api)
    
    assert result["status"] == "success"
    assert mock_api.call.call_count == 3

# Patch object attributes
def test_with_mocked_time():
    with patch('src.service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1)
        
        service = TimeService()
        assert service.get_current_year() == 2024
```

## Integration Tests (20% of tests)

```python
# tests/integration/test_user_repository.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.database import Base
from src.repositories.user_repository import UserRepository
from src.models.user import User

@pytest.fixture
def db_session():
    """Provides a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    session = Session(engine)
    yield session
    
    session.close()
    engine.dispose()

@pytest.fixture
def repository(db_session):
    return UserRepository(db_session)

@pytest.mark.integration
def test_save_and_retrieve_user(repository):
    # Arrange
    user = User(email="test@example.com", name="Test User")
    
    # Act
    repository.save(user)
    retrieved = repository.find_by_email("test@example.com")
    
    # Assert
    assert retrieved is not None
    assert retrieved.email == user.email
    assert retrieved.name == user.name

@pytest.mark.integration
def test_delete_user(repository):
    user = User(email="test@example.com", name="Test User")
    repository.save(user)
    
    repository.delete(user.id)
    
    assert repository.find_by_id(user.id) is None
```

## Async Testing

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_user_fetch():
    service = AsyncUserService()
    user = await service.fetch_user(123)
    assert user.id == 123

# Async fixtures
@pytest.fixture
async def async_db():
    db = AsyncDatabase()
    await db.connect()
    yield db
    await db.disconnect()

@pytest.mark.asyncio
async def test_with_async_fixture(async_db):
    await async_db.save({"id": 1, "name": "Test"})
    result = await async_db.find(1)
    assert result["name"] == "Test"
```

## Test Factory Pattern

```python
# tests/factories.py
from src.models.user import User

class UserFactory:
    _id_counter = 1
    
    @classmethod
    def create(cls, **kwargs) -> User:
        defaults = {
            'id': str(cls._id_counter),
            'email': f'user{cls._id_counter}@example.com',
            'name': f'User {cls._id_counter}',
            'role': 'user',
            'is_active': True,
        }
        cls._id_counter += 1
        return User(**{**defaults, **kwargs})
    
    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[User]:
        return [cls.create(**kwargs) for _ in range(count)]

# Usage
def test_admin_permissions():
    admin = UserFactory.create(role='admin')
    user = UserFactory.create()
    
    assert admin.can_delete_users() is True
    assert user.can_delete_users() is False

def test_bulk_operations():
    users = UserFactory.create_batch(10, is_active=True)
    assert len(users) == 10
    assert all(u.is_active for u in users)
```

## Edge Cases and Error Testing

```python
import pytest

def test_boundary_values():
    validator = AgeValidator(min_age=18, max_age=120)
    
    # Below minimum
    assert validator.is_valid(17) is False
    # At minimum
    assert validator.is_valid(18) is True
    # Above maximum
    assert validator.is_valid(121) is False

def test_empty_and_null_values():
    validator = EmailValidator()
    
    assert validator.validate(None).is_valid is False
    assert validator.validate("").is_valid is False
    assert validator.validate("   ").is_valid is False

def test_exception_handling():
    service = FileService()
    
    with pytest.raises(FileNotFoundError):
        service.read("nonexistent.txt")
    
    with pytest.raises(PermissionError):
        service.read("/root/protected.txt")
    
    # Test exception message
    with pytest.raises(ValueError, match="Invalid file format"):
        service.parse("invalid.txt")
```

## Coverage Commands

```bash
# Run tests with coverage
pytest --cov=src

# Generate HTML report
pytest --cov=src --cov-report=html

# Check coverage threshold (fail if below 80%)
pytest --cov=src --cov-fail-under=80

# Show missing lines
pytest --cov=src --cov-report=term-missing

# Run only unit tests with coverage
pytest tests/unit/ --cov=src

# Run specific test file
pytest tests/unit/test_user_service.py -v
```

## pytest Markers

```python
# tests/conftest.py
import pytest

# Define custom markers
pytest.register_marker("slow", "Slow running test")
pytest.register_marker("integration", "Integration test")

# tests/test_example.py
@pytest.mark.slow
def test_slow_operation():
    # This test takes a long time
    pass

@pytest.mark.integration
def test_database_integration():
    # Tests database
    pass

# Run specific markers
# pytest -m "not slow"  # Skip slow tests
# pytest -m integration  # Only integration tests
```

## Best Practices

1. **Use fixtures** for setup/teardown
2. **Parametrize tests** to avoid duplication
3. **Mock external dependencies** (APIs, databases in unit tests)
4. **Use descriptive test names** (test_user_registration_fails_with_invalid_email)
5. **Follow AAA pattern** (Arrange, Act, Assert)
6. **Test edge cases** (empty, null, boundary values)
7. **Keep tests fast** (< 1ms for unit tests)
8. **Use markers** to organize tests
9. **Aim for 80%+ coverage** on critical paths
10. **Run tests in CI/CD**

## Anti-Patterns to Avoid

❌ **Testing implementation details**
```python
def test_internal_helper_called():
    service._internal_helper()  # Don't test private methods
```

✅ **Test public behavior**
```python
def test_service_produces_correct_result():
    result = service.public_method()
    assert result == expected_value
```

❌ **Test interdependence**
```python
test_user = None

def test_step_1():
    global test_user
    test_user = create_user()  # State leak!

def test_step_2():
    update_user(test_user)  # Depends on test_step_1
```

✅ **Independent tests**
```python
@pytest.fixture
def user():
    return create_user()

def test_step_1(user):
    # Independent

def test_step_2(user):
    # Independent
```

## Quick Reference

```bash
# Run all tests
pytest

# Run with output
pytest -v

# Run specific file
pytest tests/unit/test_user.py

# Run specific test
pytest tests/unit/test_user.py::test_create_user

# Run with coverage
pytest --cov=src --cov-report=html

# Run only failed tests
pytest --lf

# Stop at first failure
pytest -x

# Run in parallel (requires pytest-xdist)
pytest -n auto
```
