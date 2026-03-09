# Node.js Testing Guide

---
**Language:** Node.js (JavaScript/TypeScript)
**Test Framework:** Jest, Vitest, Mocha
**Integration Testing:** Supertest
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

### Example: API Endpoint with TDD

**Step 1: Write the test (RED)**
```javascript
// tests/api/users.test.js
import request from 'supertest';
import { app } from '../../src/app.js';

describe('POST /api/users', () => {
  it('should create a new user', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({
        email: 'test@example.com',
        name: 'Test User'
      })
      .expect(201);
    
    expect(response.body).toHaveProperty('id');
    expect(response.body.email).toBe('test@example.com');
    expect(response.body.name).toBe('Test User');
  });
});

// Run: npm test
// Expected: FAIL - Route doesn't exist
```

**Step 2: Minimal implementation (GREEN)**
```javascript
// src/app.js
import express from 'express';

export const app = express();
app.use(express.json());

let users = [];
let idCounter = 1;

app.post('/api/users', (req, res) => {
  const { email, name } = req.body;
  const user = {
    id: idCounter++,
    email,
    name
  };
  users.push(user);
  res.status(201).json(user);
});

// Run: npm test
// Expected: PASS
```

**Step 3: Refactor (REFACTOR)**
```javascript
// src/routes/users.js
import express from 'express';
import { UserService } from '../services/user-service.js';

const router = express.Router();
const userService = new UserService();

router.post('/', async (req, res, next) => {
  try {
    const { email, name } = req.body;
    const user = await userService.createUser(email, name);
    res.status(201).json(user);
  } catch (error) {
    next(error);
  }
});

export { router as userRouter };

// Run: npm test
// Expected: Still PASS
```

## Project Structure

```
project/
├── package.json
├── jest.config.js
├── src/
│   ├── app.js
│   ├── server.js
│   ├── routes/
│   │   └── users.js
│   ├── services/
│   │   └── user-service.js
│   ├── repositories/
│   │   └── user-repository.js
│   └── middleware/
│       └── error-handler.js
└── tests/
    ├── unit/
    │   ├── services/
    │   │   └── user-service.test.js
    │   └── middleware/
    │       └── error-handler.test.js
    └── integration/
        └── api/
            └── users.test.js
```

## Jest Configuration

```javascript
// jest.config.js
export default {
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/__tests__/**/*.js', '**/*.test.js', '**/*.spec.js'],
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/server.js',
    '!src/**/__tests__/**'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testTimeout: 10000
};
```

## Unit Tests (70% of tests)

### Testing Services

```javascript
// tests/unit/services/user-service.test.js
import { UserService } from '../../../src/services/user-service.js';

describe('UserService', () => {
  let service;
  let mockRepository;
  
  beforeEach(() => {
    mockRepository = {
      save: jest.fn(),
      findById: jest.fn(),
      findByEmail: jest.fn()
    };
    service = new UserService(mockRepository);
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  describe('createUser', () => {
    it('should create user with valid data', async () => {
      const userData = { email: 'test@example.com', name: 'Test' };
      mockRepository.save.mockResolvedValue({ id: '123', ...userData });
      
      const result = await service.createUser(userData.email, userData.name);
      
      expect(result).toHaveProperty('id');
      expect(result.email).toBe(userData.email);
      expect(mockRepository.save).toHaveBeenCalledWith(
        expect.objectContaining(userData)
      );
    });
    
    it('should throw error when email already exists', async () => {
      mockRepository.findByEmail.mockResolvedValue({ id: '123' });
      
      await expect(
        service.createUser('existing@example.com', 'Test')
      ).rejects.toThrow('Email already exists');
    });
  });
  
  describe('getUser', () => {
    it('should return user when found', async () => {
      const user = { id: '123', email: 'test@example.com' };
      mockRepository.findById.mockResolvedValue(user);
      
      const result = await service.getUser('123');
      
      expect(result).toEqual(user);
    });
    
    it('should throw error when user not found', async () => {
      mockRepository.findById.mockResolvedValue(null);
      
      await expect(service.getUser('999')).rejects.toThrow('User not found');
    });
  });
});
```

### Testing Middleware

```javascript
// tests/unit/middleware/error-handler.test.js
import { errorHandler } from '../../../src/middleware/error-handler.js';
import { ApplicationError } from '../../../src/errors/index.js';

describe('errorHandler', () => {
  let req, res, next;
  
  beforeEach(() => {
    req = {};
    res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    };
    next = jest.fn();
  });
  
  it('should handle ApplicationError', () => {
    const error = new ApplicationError('Test error', 400);
    
    errorHandler(error, req, res, next);
    
    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({
      error: {
        message: 'Test error',
        code: error.code
      }
    });
  });
  
  it('should handle unexpected errors', () => {
    const error = new Error('Unexpected');
    
    errorHandler(error, req, res, next);
    
    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith({
      error: {
        message: 'Internal server error',
        code: 'INTERNAL_ERROR'
      }
    });
  });
});
```

## Integration Tests with Supertest (20% of tests)

```javascript
// tests/integration/api/users.test.js
import request from 'supertest';
import { app } from '../../../src/app.js';
import { database } from '../../../src/database.js';

describe('User API Integration', () => {
  beforeAll(async () => {
    await database.connect();
  });
  
  afterAll(async () => {
    await database.disconnect();
  });
  
  beforeEach(async () => {
    await database.clearUsers();
  });
  
  describe('POST /api/users', () => {
    it('should create a new user', async () => {
      const userData = {
        email: 'test@example.com',
        name: 'Test User'
      };
      
      const response = await request(app)
        .post('/api/users')
        .send(userData)
        .expect(201)
        .expect('Content-Type', /json/);
      
      expect(response.body).toMatchObject({
        id: expect.any(String),
        email: userData.email,
        name: userData.name
      });
    });
    
    it('should return 400 with invalid email', async () => {
      const response = await request(app)
        .post('/api/users')
        .send({
          email: 'invalid-email',
          name: 'Test'
        })
        .expect(400);
      
      expect(response.body.error).toBeDefined();
      expect(response.body.error.message).toMatch(/email/i);
    });
    
    it('should return 409 when email already exists', async () => {
      const userData = {
        email: 'test@example.com',
        name: 'Test'
      };
      
      await request(app).post('/api/users').send(userData);
      
      await request(app)
        .post('/api/users')
        .send(userData)
        .expect(409);
    });
  });
  
  describe('GET /api/users/:id', () => {
    it('should return user by id', async () => {
      const createResponse = await request(app)
        .post('/api/users')
        .send({ email: 'test@example.com', name: 'Test' });
      
      const userId = createResponse.body.id;
      
      const response = await request(app)
        .get(`/api/users/${userId}`)
        .expect(200);
      
      expect(response.body.id).toBe(userId);
      expect(response.body.email).toBe('test@example.com');
    });
    
    it('should return 404 when user not found', async () => {
      await request(app)
        .get('/api/users/nonexistent-id')
        .expect(404);
    });
  });
  
  describe('PUT /api/users/:id', () => {
    it('should update user', async () => {
      const createResponse = await request(app)
        .post('/api/users')
        .send({ email: 'test@example.com', name: 'Old Name' });
      
      const userId = createResponse.body.id;
      
      const response = await request(app)
        .put(`/api/users/${userId}`)
        .send({ name: 'New Name' })
        .expect(200);
      
      expect(response.body.name).toBe('New Name');
    });
  });
  
  describe('DELETE /api/users/:id', () => {
    it('should delete user', async () => {
      const createResponse = await request(app)
        .post('/api/users')
        .send({ email: 'test@example.com', name: 'Test' });
      
      const userId = createResponse.body.id;
      
      await request(app)
        .delete(`/api/users/${userId}`)
        .expect(204);
      
      await request(app)
        .get(`/api/users/${userId}`)
        .expect(404);
    });
  });
});
```

## Async Testing

```javascript
describe('Async Operations', () => {
  it('should handle promises', async () => {
    const result = await fetchData();
    expect(result).toBeDefined();
  });
  
  it('should handle promise rejections', async () => {
    await expect(fetchInvalidData()).rejects.toThrow('Invalid data');
  });
  
  it('should handle callbacks with done', (done) => {
    fetchDataWithCallback((err, data) => {
      expect(err).toBeNull();
      expect(data).toBeDefined();
      done();
    });
  });
  
  it('should timeout after delay', async () => {
    jest.setTimeout(6000);
    await expect(slowOperation()).rejects.toThrow('Timeout');
  }, 6000);
});
```

## Mocking External Services

```javascript
// Mock fetch API
global.fetch = jest.fn();

describe('ExternalAPIService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  it('should fetch data from external API', async () => {
    const mockData = { id: 1, name: 'Test' };
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => mockData
    });
    
    const service = new ExternalAPIService();
    const result = await service.fetchData();
    
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      '
    );
  });
  
  it('should handle API errors', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500
    });
    
    const service = new ExternalAPIService();
    
    await expect(service.fetchData()).rejects.toThrow('API error');
  });
});
```

## Database Testing with Test Containers

```javascript
// tests/integration/database.test.js
import { GenericContainer } from 'testcontainers';
import { Pool } from 'pg';

describe('Database Integration', () => {
  let container;
  let pool;
  
  beforeAll(async () => {
    // Start PostgreSQL container
    container = await new GenericContainer('postgres:15')
      .withEnvironment({
        POSTGRES_USER: 'test',
        POSTGRES_PASSWORD: 'test',
        POSTGRES_DB: 'testdb'
      })
      .withExposedPorts(5432)
      .start();
    
    const port = container.getMappedPort(5432);
    
    pool = new Pool({
      host: 'localhost',
      port,
      user: 'test',
      password: 'test',
      database: 'testdb'
    });
    
    // Run migrations
    await runMigrations(pool);
  }, 60000);
  
  afterAll(async () => {
    await pool.end();
    await container.stop();
  });
  
  beforeEach(async () => {
    await pool.query('TRUNCATE TABLE users CASCADE');
  });
  
  it('should save and retrieve user', async () => {
    const user = { email: 'test@example.com', name: 'Test' };
    
    const insertResult = await pool.query(
      'INSERT INTO users (email, name) VALUES ($1, $2) RETURNING *',
      [user.email, user.name]
    );
    
    const selectResult = await pool.query(
      'SELECT * FROM users WHERE id = $1',
      [insertResult.rows[0].id]
    );
    
    expect(selectResult.rows[0].email).toBe(user.email);
  });
});
```

## Testing Streams

```javascript
import { Readable, Writable } from 'stream';
import { pipeline } from 'stream/promises';

describe('StreamProcessor', () => {
  it('should process stream data', async () => {
    const input = Readable.from(['hello', ' ', 'world']);
    const output = [];
    
    const processStream = new Writable({
      write(chunk, encoding, callback) {
        output.push(chunk.toString().toUpperCase());
        callback();
      }
    });
    
    await pipeline(input, processStream);
    
    expect(output).toEqual(['HELLO', ' ', 'WORLD']);
  });
});
```

## Test Factories

```javascript
// tests/factories/user-factory.js
export class UserFactory {
  static idCounter = 1;
  
  static create(overrides = {}) {
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
  
  static createBatch(count, overrides = {}) {
    return Array.from({ length: count }, () => this.create(overrides));
  }
}

// Usage
test('should handle admin users', () => {
  const admin = UserFactory.create({ role: 'admin' });
  const user = UserFactory.create();
  
  expect(admin.canDeleteUsers()).toBe(true);
  expect(user.canDeleteUsers()).toBe(false);
});
```

## Edge Cases Testing

```javascript
describe('Edge Cases', () => {
  test.each([
    [null, false],
    [undefined, false],
    ['', false],
    ['   ', false],
    ['valid@email.com', true],
  ])('validateEmail(%s) should return %s', (email, expected) => {
    expect(validateEmail(email)).toBe(expected);
  });
  
  it('should handle large datasets', async () => {
    const largeArray = Array.from({ length: 10000 }, (_, i) => i);
    const result = await processLargeArray(largeArray);
    expect(result.length).toBe(10000);
  });
  
  it('should handle concurrent requests', async () => {
    const promises = Array.from({ length: 100 }, () => 
      request(app).get('/api/health')
    );
    
    const results = await Promise.all(promises);
    
    expect(results.every(r => r.status === 200)).toBe(true);
  });
});
```

## Coverage Commands

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch

# Run specific file
npm test users.test.js

# Run integration tests only
npm test tests/integration

# Run with verbose output
npm test -- --verbose

# Update snapshots
npm test -- --updateSnapshot
```

## Best Practices

1. **Use Supertest** for API testing
2. **Mock external services** (databases, APIs)
3. **Use test containers** for real database testing
4. **Test error handling** thoroughly
5. **Test middleware** separately
6. **Use factories** for test data
7. **Clean up** after tests (database, files)
8. **Test async code** properly (async/await)
9. **Aim for 80%+ coverage** on routes and services
10. **Keep tests isolated** and independent

## Anti-Patterns to Avoid

❌ **Not cleaning up database**
```javascript
// Bad: Data persists between tests
afterAll(() => {
  // No cleanup
});
```

✅ **Clean up after each test**
```javascript
afterEach(async () => {
  await database.clearAll();
});
```

❌ **Testing private implementation**
```javascript
// Bad: Testing internal state
expect(service._internalCache).toBeDefined();
```

✅ **Test public API**
```javascript
// Good: Test behavior
expect(await service.getData()).toEqual(expectedData);
```

❌ **Hardcoding ports and URLs**
```javascript
// Bad: Fixed port
const server = app.listen(3000);
```

✅ **Dynamic port assignment**
```javascript
// Good: Let OS assign port
const server = app.listen(0);
const port = server.address().port;
```

## Quick Reference

```bash
# Run tests
npm test

# Coverage
npm test -- --coverage

# Watch
npm test -- --watch

# Specific test
npm test users

# Verbose
npm test -- --verbose

# Only failed
npm test -- --onlyFailures

# Clear cache
npm test -- --clearCache
```
