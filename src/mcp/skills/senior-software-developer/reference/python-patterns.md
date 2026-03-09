# Python Code Quality & Patterns

---
**Language:** Python
**Focus:** SOLID principles, Pythonic patterns, common anti-patterns
---

## SOLID Principles in Python

### Single Responsibility Principle (SRP)

**Bad:**
```python
class User:
    def __init__(self, email: str, name: str):
        self.email = email
        self.name = name
    
    def save_to_database(self):
        # Database logic
        conn = sqlite3.connect('users.db')
        conn.execute(...)
    
    def send_welcome_email(self):
        # Email logic
        smtp.send(...)
    
    def validate_password(self, password: str):
        # Validation logic
        return len(password) >= 8
```

**Good:**
```python
from dataclasses import dataclass

@dataclass
class User:
    """User data model - only data and behavior related to user itself"""
    email: str
    name: str
    
    def is_admin(self) -> bool:
        return self.email.endswith('@admin.com')

class UserRepository:
    """Handles user persistence"""
    def __init__(self, db: Database):
        self.db = db
    
    def save(self, user: User) -> None:
        self.db.execute("INSERT INTO users ...")

class EmailService:
    """Handles email sending"""
    def send_welcome_email(self, user: User) -> None:
        self.smtp.send(to=user.email, ...)

class PasswordValidator:
    """Handles password validation"""
    def __init__(self, min_length: int = 8):
        self.min_length = min_length
    
    def validate(self, password: str) -> bool:
        return len(password) >= self.min_length
```

### Open/Closed Principle (OCP)

**Bad:**
```python
class PaymentProcessor:
    def process_payment(self, payment_type: str, amount: float):
        if payment_type == 'credit_card':
            # Credit card logic
            pass
        elif payment_type == 'paypal':
            # PayPal logic
            pass
        elif payment_type == 'crypto':
            # Had to modify existing code!
            pass
```

**Good:**
```python
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    @abstractmethod
    async def process(self, amount: float) -> None:
        pass

class CreditCardPayment(PaymentMethod):
    async def process(self, amount: float) -> None:
        # Credit card logic
        pass

class PayPalPayment(PaymentMethod):
    async def process(self, amount: float) -> None:
        # PayPal logic
        pass

class CryptoPayment(PaymentMethod):
    async def process(self, amount: float) -> None:
        # Crypto logic - no modification to existing code!
        pass

class PaymentProcessor:
    def __init__(self, method: PaymentMethod):
        self.method = method
    
    async def process_payment(self, amount: float) -> None:
        await self.method.process(amount)
```

### Liskov Substitution Principle (LSP)

**Bad:**
```python
class Rectangle:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
    
    def area(self) -> int:
        return self.width * self.height

class Square(Rectangle):
    def __init__(self, side: int):
        super().__init__(side, side)
    
    @property
    def width(self) -> int:
        return self._width
    
    @width.setter
    def width(self, value: int):
        self._width = value
        self._height = value  # Violates LSP - unexpected behavior!
```

**Good:**
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> int:
        pass

class Rectangle(Shape):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
    
    def area(self) -> int:
        return self.width * self.height

class Square(Shape):
    def __init__(self, side: int):
        self.side = side
    
    def area(self) -> int:
        return self.side * self.side
```

### Interface Segregation Principle (ISP)

**Bad:**
```python
class Worker(ABC):
    @abstractmethod
    def work(self):
        pass
    
    @abstractmethod
    def eat(self):
        pass
    
    @abstractmethod
    def sleep(self):
        pass

class Robot(Worker):
    def work(self):
        # Works
        pass
    
    def eat(self):
        # Robots don't eat - forced to implement!
        raise NotImplementedError("Robots don't eat")
    
    def sleep(self):
        # Robots don't sleep - forced to implement!
        raise NotImplementedError("Robots don't sleep")
```

**Good:**
```python
class Workable(ABC):
    @abstractmethod
    def work(self):
        pass

class Eatable(ABC):
    @abstractmethod
    def eat(self):
        pass

class Sleepable(ABC):
    @abstractmethod
    def sleep(self):
        pass

class Human(Workable, Eatable, Sleepable):
    def work(self):
        print("Working...")
    
    def eat(self):
        print("Eating...")
    
    def sleep(self):
        print("Sleeping...")

class Robot(Workable):
    def work(self):
        print("Working 24/7...")
```

### Dependency Inversion Principle (DIP)

**Bad:**
```python
class EmailService:
    def send(self, message: str) -> None:
        # Send email
        pass

class NotificationService:
    def __init__(self):
        self.email_service = EmailService()  # Tight coupling!
    
    def notify(self, message: str) -> None:
        self.email_service.send(message)
```

**Good:**
```python
from abc import ABC, abstractmethod

class MessageSender(ABC):
    @abstractmethod
    def send(self, message: str) -> None:
        pass

class EmailService(MessageSender):
    def send(self, message: str) -> None:
        # Send email
        pass

class SMSService(MessageSender):
    def send(self, message: str) -> None:
        # Send SMS
        pass

class NotificationService:
    def __init__(self, sender: MessageSender):
        self.sender = sender  # Depends on abstraction
    
    def notify(self, message: str) -> None:
        self.sender.send(message)
```

## Pythonic Design Patterns

### Factory Pattern

```python
from enum import Enum
from typing import Protocol

class DatabaseType(Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"

class Database(Protocol):
    def connect(self) -> None: ...
    def execute(self, query: str) -> list: ...

class PostgresDatabase:
    def connect(self) -> None:
        print("Connecting to PostgreSQL")
    
    def execute(self, query: str) -> list:
        return []

class MySQLDatabase:
    def connect(self) -> None:
        print("Connecting to MySQL")
    
    def execute(self, query: str) -> list:
        return []

class DatabaseFactory:
    @staticmethod
    def create(db_type: DatabaseType, config: dict) -> Database:
        match db_type:
            case DatabaseType.POSTGRES:
                return PostgresDatabase()
            case DatabaseType.MYSQL:
                return MySQLDatabase()
            case _:
                raise ValueError(f"Unknown database type: {db_type}")

# Usage
db = DatabaseFactory.create(DatabaseType.POSTGRES, {})
```

### Strategy Pattern

```python
from abc import ABC, abstractmethod
from typing import List

class SortStrategy(ABC):
    @abstractmethod
    def sort(self, data: List[int]) -> List[int]:
        pass

class QuickSort(SortStrategy):
    def sort(self, data: List[int]) -> List[int]:
        if len(data) <= 1:
            return data
        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]
        return self.sort(left) + middle + self.sort(right)

class BubbleSort(SortStrategy):
    def sort(self, data: List[int]) -> List[int]:
        arr = data.copy()
        n = len(arr)
        for i in range(n):
            for j in range(0, n-i-1):
                if arr[j] > arr[j+1]:
                    arr[j], arr[j+1] = arr[j+1], arr[j]
        return arr

class Sorter:
    def __init__(self, strategy: SortStrategy):
        self.strategy = strategy
    
    def sort(self, data: List[int]) -> List[int]:
        return self.strategy.sort(data)

# Usage
sorter = Sorter(QuickSort())
sorted_data = sorter.sort([3, 1, 4, 1, 5, 9])
```

### Context Manager Pattern

```python
from contextlib import contextmanager
from typing import Generator

class DatabaseConnection:
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def connect(self):
        print("Connected to database")
    
    def close(self):
        print("Closed database connection")

# Usage
with DatabaseConnection() as db:
    # Use database
    pass

# Or use @contextmanager decorator
@contextmanager
def temp_file(name: str) -> Generator[str, None, None]:
    try:
        f = open(name, 'w')
        yield name
    finally:
        f.close()
        os.remove(name)

# Usage
with temp_file('temp.txt') as filename:
    # Use file
    pass
```

### Singleton Pattern (Pythonic Way)

```python
# Using module-level instance (recommended)
class DatabaseConnection:
    def __init__(self):
        self.connected = False
    
    def connect(self):
        if not self.connected:
            print("Connecting...")
            self.connected = True

# In db.py
_instance = DatabaseConnection()

def get_connection():
    return _instance

# Or using __new__ (less common)
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

## Anti-Patterns to Avoid

### God Object

**Bad:**
```python
class Application:
    def connect_to_database(self): pass
    def send_email(self): pass
    def process_payment(self): pass
    def generate_report(self): pass
    def authenticate_user(self): pass
    # ... 50 more methods - does everything!
```

**Good:**
```python
class DatabaseService:
    def connect(self): pass

class EmailService:
    def send(self, to: str, message: str): pass

class PaymentService:
    def process(self, amount: float): pass

class ReportGenerator:
    def generate(self, data: dict): pass

class AuthenticationService:
    def authenticate(self, credentials: dict): pass
```

### Primitive Obsession

**Bad:**
```python
def process_order(
    order_id: str,
    customer_id: str,
    items: list[str],
    total: float,
    currency: str
):
    # Using primitives everywhere
    pass
```

**Good:**
```python
from dataclasses import dataclass
from typing import NewType

OrderId = NewType('OrderId', str)
CustomerId = NewType('CustomerId', str)

@dataclass(frozen=True)
class Money:
    amount: float
    currency: str
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

@dataclass
class OrderItem:
    name: str
    price: Money
    quantity: int

@dataclass
class Order:
    id: OrderId
    customer_id: CustomerId
    items: list[OrderItem]
    total: Money

def process_order(order: Order):
    # Type-safe, self-documenting
    pass
```

### Magic Numbers/Strings

**Bad:**
```python
if user.status == 2:  # What is 2?
    pass

if response.code == "ERR_TIMEOUT":  # Magic string
    pass
```

**Good:**
```python
from enum import Enum, auto

class UserStatus(Enum):
    ACTIVE = auto()
    SUSPENDED = auto()
    DELETED = auto()

class ErrorCode(Enum):
    TIMEOUT = "ERR_TIMEOUT"
    NOT_FOUND = "ERR_NOT_FOUND"
    UNAUTHORIZED = "ERR_UNAUTHORIZED"

if user.status == UserStatus.SUSPENDED:
    pass

if response.code == ErrorCode.TIMEOUT.value:
    pass
```

### Leaky Abstraction

**Bad:**
```python
class UserRepository:
    def get_user_with_sql(self, user_id: int) -> User:
        # Method name leaks implementation detail
        return self.db.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**Good:**
```python
class UserRepository:
    def get_user(self, user_id: int) -> User:
        # Implementation hidden, can change to NoSQL without breaking interface
        return self.db.query(User).filter_by(id=user_id).first()
```

## Error Handling Patterns

### Result Type Pattern

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Success(Generic[T]):
    value: T

@dataclass
class Failure(Generic[E]):
    error: E

Result = Union[Success[T], Failure[E]]

def fetch_user(user_id: int) -> Result[User, Exception]:
    try:
        user = api.get(f"/users/{user_id}")
        return Success(user)
    except Exception as e:
        return Failure(e)

# Usage
result = fetch_user(123)
match result:
    case Success(user):
        print(user.name)
    case Failure(error):
        print(f"Error: {error}")
```

### Custom Exception Hierarchy

```python
class ApplicationError(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code

class ValidationError(ApplicationError):
    """Input validation failed"""
    def __init__(self, message: str, fields: dict[str, str] | None = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.fields = fields

class NotFoundError(ApplicationError):
    """Resource not found"""
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", "NOT_FOUND")

class UnauthorizedError(ApplicationError):
    """User not authorized"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED")

# Usage
try:
    user = get_user(user_id)
except NotFoundError:
    return {"error": "User not found"}, 404
except UnauthorizedError:
    return {"error": "Unauthorized"}, 401
except ApplicationError as e:
    return {"error": e.message}, 500
```

### Retry with Exponential Backoff

```python
import asyncio
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar('T')

def retry_async(max_retries: int = 3, delay_ms: int = 1000):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = delay_ms * (2 ** attempt) / 1000
                    await asyncio.sleep(wait_time)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@retry_async(max_retries=3, delay_ms=1000)
async def fetch_data():
    # May fail, will retry with exponential backoff
    pass
```

## Performance Patterns

### N+1 Query Problem

**Bad:**
```python
# 1 query to get users, then N queries for their orders
users = session.query(User).all()  # 1 query
for user in users:
    orders = session.query(Order).filter_by(user_id=user.id).all()  # N queries!
```

**Good:**
```python
from sqlalchemy.orm import joinedload

# 1 query with join
users = session.query(User).options(joinedload(User.orders)).all()
```

### Caching with functools

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    # Cached automatically
    return sum(range(n))

# Manual cache control
expensive_calculation.cache_clear()
expensive_calculation.cache_info()
```

## Best Practices

1. **Use dataclasses** for data containers
2. **Use type hints** everywhere
3. **Follow PEP 8** naming conventions
4. **Use ABC** for interfaces
5. **Prefer composition** over inheritance
6. **Use context managers** for resources
7. **Handle exceptions** at appropriate levels
8. **Use enum** for constants
9. **Avoid mutable defaults** in functions
10. **Write docstrings** for public APIs
