# TypeScript Testing Guide

---
**Language:** TypeScript
**Test Framework:** Jest (recommended), Vitest
**Coverage Tool:** Jest coverage, c8
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
```typescript
// src/services/__tests__/user-service.test.ts
import { UserService } from '../user-service';

describe('UserService', () => {
  describe('register', () => {
    it('should register user with valid data', async () => {
      // Arrange
      const service = new UserService();
      const email = 'test@example.com';
      const password = 'SecurePass123!';
      
      // Act
      const result = await service.register(email, password);
      
      // Assert
      expect(result.success).toBe(true);
      expect(result.user.email).toBe(email);
      expect(result.user.password).not.toBe(password); // Should be hashed
      expect(result.user.id).toBeTruthy();
    });
  });
});

// Run: npm test
// Expected: FAIL - UserService.register doesn't exist
```

**Step 2: Minimal implementation (GREEN)**
```typescript
// src/services/user-service.ts
import bcrypt from 'bcrypt';
import { v4 as uuidv4 } from 'uuid';

interface User {
  id: string;
  email: string;
  password: string;
}

interface RegistrationResult {
  success: boolean;
  user: User;
}

export class UserService {
  async register(email: string, password: string): Promise<RegistrationResult> {
    const hashedPassword = await bcrypt.hash(password, 10);
    const user: User = {
      id: uuidv4(),
      email,
      password: hashedPassword
    };
    
    return { success: true, user };
  }
}

// Run: npm test
// Expected: PASS
```

**Step 3: Refactor (REFACTOR)**
```typescript
// Extract password hashing
export interface PasswordHasher {
  hash(password: string): Promise<string>;
}

export class BcryptHasher implements PasswordHasher {
  async hash(password: string): Promise<string> {
    return bcrypt.hash(password, 10);
  }
}

export class UserService {
  constructor(private hasher: PasswordHasher = new BcryptHasher()) {}
  
  async register(email: string, password: string): Promise<RegistrationResult> {
    const hashedPassword = await this.hasher.hash(password);
    const user: User = {
      id: uuidv4(),
      email,
      password: hashedPassword
    };
    
    return { success: true, user };
  }
}

// Run: npm test
// Expected: Still PASS (update test to inject hasher)
```

## Project Structure

```
project/
├── package.json
├── jest.config.js
├── tsconfig.json
├── src/
│   ├── models/
│   │   └── user.ts
│   ├── services/
│   │   ├── user-service.ts
│   │   └── __tests__/
│   │       └── user-service.test.ts
│   ├── repositories/
│   │   ├── user-repository.ts
│   │   └── __tests__/
│   │       └── user-repository.test.ts
│   └── utils/
│       ├── validators.ts
│       └── __tests__/
│           └── validators.test.ts
└── tests/
    └── integration/
        └── user-flow.test.ts
```

## Jest Configuration (jest.config.js)

```javascript
export default {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/__tests__/**/*.ts', '**/*.test.ts', '**/*.spec.ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
    '!src/index.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts']
};
```

## Unit Tests (70% of tests)

### Basic Test Structure

```typescript
describe('Calculator', () => {
  let calculator: Calculator;
  
  beforeEach(() => {
    // Runs before each test
    calculator = new Calculator();
  });
  
  afterEach(() => {
    // Runs after each test
    jest.clearAllMocks();
  });
  
  describe('add', () => {
    it('should add two positive numbers', () => {
      expect(calculator.add(2, 3)).toBe(5);
    });
    
    it('should handle negative numbers', () => {
      expect(calculator.add(-2, 3)).toBe(1);
    });
  });
  
  describe('divide', () => {
    it('should divide two numbers', () => {
      expect(calculator.divide(10, 2)).toBe(5);
    });
    
    it('should throw error when dividing by zero', () => {
      expect(() => calculator.divide(10, 0)).toThrow('Division by zero');
    });
  });
});
```

### Parametrized Tests (test.each)

```typescript
describe('AgeValidator', () => {
  const validator = new AgeValidator(18, 120);
  
  test.each([
    [17, false],  // Below minimum
    [18, true],   // Minimum
    [19, true],   // Above minimum
    [119, true],  // Below maximum
    [120, true],  // Maximum
    [121, false], // Above maximum
  ])('isValid(%i) should return %s', (age, expected) => {
    expect(validator.isValid(age)).toBe(expected);
  });
});

describe('EmailValidator', () => {
  const validator = new EmailValidator();
  
  test.each([
    ['test@example.com', true],
    ['invalid.email', false],
    ['@example.com', false],
    ['test@', false],
    ['', false],
    [null, false],
  ])('validate(%s) should return isValid=%s', (email, expectedValid) => {
    const result = validator.validate(email);
    expect(result.isValid).toBe(expectedValid);
  });
});
```

### Testing Async Code

```typescript
describe('UserService', () => {
  it('should fetch user asynchronously', async () => {
    const service = new UserService();
    
    const user = await service.fetchUser(123);
    
    expect(user.id).toBe(123);
  });
  
  it('should handle errors in async operations', async () => {
    const service = new UserService();
    
    await expect(service.fetchUser(-1)).rejects.toThrow('Invalid user ID');
  });
  
  it('should timeout after 5 seconds', async () => {
    jest.setTimeout(6000);
    const service = new UserService();
    
    await expect(service.slowOperation()).rejects.toThrow('Timeout');
  });
});
```

## Mocking with Jest

### Mock Functions

```typescript
describe('UserService', () => {
  it('should call repository to fetch user', async () => {
    const mockRepository = {
      findById: jest.fn().mockResolvedValue({
        id: 1,
        name: 'Alice',
        email: 'alice@example.com'
      })
    };
    
    const service = new UserService(mockRepository);
    
    const user = await service.getUser(1);
    
    expect(user.name).toBe('Alice');
    expect(mockRepository.findById).toHaveBeenCalledWith(1);
    expect(mockRepository.findById).toHaveBeenCalledTimes(1);
  });
});
```

### Mock Modules

```typescript
// Mock external module
jest.mock('axios');
import axios from 'axios';
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('ApiService', () => {
  it('should fetch data from API', async () => {
    mockedAxios.get.mockResolvedValue({
      data: { id: 1, name: 'Test' }
    });
    
    const service = new ApiService();
    const result = await service.fetchData();
    
    expect(result.name).toBe('Test');
    expect(mockedAxios.get).toHaveBeenCalledWith('
  });
});
```

### Partial Mocks

```typescript
import * as utils from '../utils';

describe('Service', () => {
  it('should use mocked utility', () => {
    jest.spyOn(utils, 'generateId').mockReturnValue('mock-id');
    
    const service = new Service();
    const result = service.create({ name: 'Test' });
    
    expect(result.id).toBe('mock-id');
    expect(utils.generateId).toHaveBeenCalled();
  });
});
```

### Mock Timers

```typescript
describe('DelayedService', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  it('should execute callback after delay', () => {
    const callback = jest.fn();
    const service = new DelayedService();
    
    service.scheduleTask(callback, 1000);
    
    expect(callback).not.toHaveBeenCalled();
    
    jest.advanceTimersByTime(1000);
    
    expect(callback).toHaveBeenCalledTimes(1);
  });
  
  it('should handle multiple scheduled tasks', () => {
    const callback1 = jest.fn();
    const callback2 = jest.fn();
    
    const service = new DelayedService();
    service.scheduleTask(callback1, 1000);
    service.scheduleTask(callback2, 2000);
    
    jest.advanceTimersByTime(1500);
    expect(callback1).toHaveBeenCalled();
    expect(callback2).not.toHaveBeenCalled();
    
    jest.advanceTimersByTime(500);
    expect(callback2).toHaveBeenCalled();
  });
});
```

## Integration Tests (20% of tests)

```typescript
// tests/integration/user-flow.test.ts
import request from 'supertest';
import { app } from '../../src/app';
import { database } from '../../src/database';

describe('User Registration Flow', () => {
  beforeAll(async () => {
    await database.connect();
  });
  
  afterAll(async () => {
    await database.disconnect();
  });
  
  afterEach(async () => {
    await database.clearUsers();
  });
  
  it('should register new user and return auth token', async () => {
    const response = await request(app)
      .post('/api/register')
      .send({
        email: 'newuser@example.com',
        password: 'SecurePass123!',
        name: 'New User'
      })
      .expect(201);
    
    expect(response.body).toHaveProperty('token');
    expect(response.body.user.email).toBe('newuser@example.com');
    
    // Verify can login with credentials
    const loginResponse = await request(app)
      .post('/api/login')
      .send({
        email: 'newuser@example.com',
        password: 'SecurePass123!'
      })
      .expect(200);
    
    expect(loginResponse.body).toHaveProperty('token');
  });
});
```

## Test Fixtures and Helpers

```typescript
// tests/fixtures/user-factory.ts
export class UserFactory {
  private static idCounter = 1;
  
  static create(overrides?: Partial<User>): User {
    const id = this.idCounter++;
    return {
      id: id.toString(),
      email: `user${id}@example.com`,
      name: `User ${id}`,
      role: 'user',
      isActive: true,
      ...overrides
    };
  }
  
  static createBatch(count: number, overrides?: Partial<User>): User[] {
    return Array.from({ length: count }, () => this.create(overrides));
  }
}

// Usage
describe('UserService', () => {
  it('should handle admin users', () => {
    const admin = UserFactory.create({ role: 'admin' });
    const user = UserFactory.create();
    
    expect(admin.canDeleteUsers()).toBe(true);
    expect(user.canDeleteUsers()).toBe(false);
  });
});
```

### Test Builder Pattern

```typescript
class OrderBuilder {
  private order: Partial<Order> = {
    id: 'order-1',
    items: [],
    total: 0,
    status: 'pending'
  };
  
  withItems(...items: OrderItem[]): this {
    this.order.items = items;
    this.order.total = items.reduce((sum, item) => sum + item.price, 0);
    return this;
  }
  
  withStatus(status: OrderStatus): this {
    this.order.status = status;
    return this;
  }
  
  build(): Order {
    return this.order as Order;
  }
}

// Usage
test('should calculate shipping for completed order', () => {
  const order = new OrderBuilder()
    .withItems(
      { name: 'Item 1', price: 10 },
      { name: 'Item 2', price: 20 }
    )
    .withStatus('completed')
    .build();
  
  expect(calculateShipping(order)).toBe(5);
});
```

## Edge Cases and Error Testing

```typescript
describe('FileReader', () => {
  it('should throw error when file not found', async () => {
    const reader = new FileReader();
    
    await expect(reader.read('nonexistent.txt'))
      .rejects.toThrow('File not found');
  });
  
  it('should throw error when file is too large', async () => {
    const reader = new FileReader({ maxSize: 1024 });
    
    await expect(reader.read('large-file.txt'))
      .rejects.toThrow('File exceeds maximum size');
  });
  
  it('should handle null and undefined gracefully', () => {
    const parser = new DataParser();
    
    expect(() => parser.parse(null)).toThrow('Data cannot be null');
    expect(() => parser.parse(undefined)).toThrow('Data cannot be undefined');
  });
});

describe('BoundaryTesting', () => {
  test.each([
    [Number.MIN_SAFE_INTEGER, true],
    [Number.MAX_SAFE_INTEGER, true],
    [Infinity, false],
    [-Infinity, false],
    [NaN, false],
  ])('isValidNumber(%d) should return %s', (value, expected) => {
    expect(isValidNumber(value)).toBe(expected);
  });
});
```

## Snapshot Testing

```typescript
import { render } from '@testing-library/react';

describe('UserProfile', () => {
  it('should match snapshot', () => {
    const user = UserFactory.create();
    const { container } = render(<UserProfile user={user} />);
    
    expect(container).toMatchSnapshot();
  });
  
  it('should match inline snapshot', () => {
    const data = formatUserData({ name: 'Alice', age: 30 });
    
    expect(data).toMatchInlineSnapshot(`
      Object {
        "age": 30,
        "name": "Alice",
      }
    `);
  });
});
```

## Coverage Commands

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test user-service.test.ts

# Run in watch mode
npm test -- --watch

# Run tests matching pattern
npm test -- --testNamePattern="should register user"

# Update snapshots
npm test -- --updateSnapshot

# Run with verbose output
npm test -- --verbose
```

## Test Organization

```typescript
// Group related tests
describe('UserService', () => {
  describe('registration', () => {
    it('should register with valid data', () => {});
    it('should reject invalid email', () => {});
    it('should reject weak password', () => {});
  });
  
  describe('authentication', () => {
    it('should login with correct credentials', () => {});
    it('should reject wrong password', () => {});
    it('should lock account after failed attempts', () => {});
  });
});

// Use describe.each for similar test suites
describe.each([
  ['UserService', new UserService()],
  ['AdminService', new AdminService()],
])('%s', (name, service) => {
  it('should have a create method', () => {
    expect(service.create).toBeDefined();
  });
});
```

## Best Practices

1. **Use descriptive test names** - "should register user with valid email"
2. **Follow AAA pattern** - Arrange, Act, Assert
3. **One assertion per test** - Or at least one concept
4. **Mock external dependencies** - APIs, databases, file system
5. **Test edge cases** - null, undefined, empty arrays, boundary values
6. **Use test.each** for parametrized tests
7. **Keep tests fast** - Unit tests < 10ms
8. **Use factories** for test data
9. **Clear mocks** between tests
10. **Aim for 80%+ coverage** on business logic

## Anti-Patterns to Avoid

❌ **Testing implementation details**
```typescript
it('should call private method', () => {
  const spy = jest.spyOn(service as any, '_privateMethod');
  service.publicMethod();
  expect(spy).toHaveBeenCalled();
});
```

✅ **Test public behavior**
```typescript
it('should produce correct result', () => {
  const result = service.publicMethod();
  expect(result).toBe(expectedValue);
});
```

❌ **Shared state between tests**
```typescript
let testUser: User;

it('test 1', () => {
  testUser = createUser();  // State leak!
});

it('test 2', () => {
  updateUser(testUser);  // Depends on test 1
});
```

✅ **Independent tests**
```typescript
it('test 1', () => {
  const user = createUser();  // Independent
});

it('test 2', () => {
  const user = createUser();  // Independent
});
```

❌ **Too many assertions**
```typescript
it('should do everything', () => {
  expect(user.name).toBe('Alice');
  expect(user.email).toBe('alice@example.com');
  expect(user.isActive).toBe(true);
  expect(user.role).toBe('admin');
  // ... 20 more assertions
});
```

✅ **Focused tests**
```typescript
it('should have correct name', () => {
  expect(user.name).toBe('Alice');
});

it('should be active by default', () => {
  expect(user.isActive).toBe(true);
});
```

## Quick Reference

```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# Specific file
npm test user-service

# Update snapshots
npm test -- -u

# Verbose
npm test -- --verbose

# Only changed files
npm test -- --onlyChanged

# Clear cache
npm test -- --clearCache
```
