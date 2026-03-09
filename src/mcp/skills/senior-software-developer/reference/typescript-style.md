# TypeScript Style Guide

---
**Language:** TypeScript
**Use when:** Working with TypeScript projects, React apps with TypeScript, or Node.js with TypeScript
---

## Naming Conventions

```typescript
// Files: kebab-case
// user-service.ts, user-repository.ts

// Interfaces: PascalCase (no 'I' prefix)
interface User {
  id: number;
  email: string;
}

// Types: PascalCase
type UserId = number;
type UserRole = 'admin' | 'user' | 'guest';

// Classes: PascalCase
class UserService {
  // Private fields: camelCase with # or private
  #database: Database;
  private logger: Logger;
  
  // Public properties: camelCase
  maxRetries = 3;
  
  constructor(database: Database, logger: Logger) {
    this.#database = database;
    this.logger = logger;
  }
  
  // Methods: camelCase
  async findById(id: number): Promise<User | null> {
    return this.#database.query<User>(id);
  }
}

// Functions: camelCase
function calculateTotal(items: Item[]): number {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// Constants: UPPER_CASE
const MAX_RETRIES = 3;
const DEFAULT_TIMEOUT = 30000;

// Enums: PascalCase
enum UserRole {
  Admin = 'admin',
  User = 'user',
  Guest = 'guest'
}
```

## Type System Best Practices

```typescript
// Prefer interfaces for object shapes
interface User {
  id: number;
  email: string;
  readonly createdAt: Date; // Immutable property
  roles: readonly string[]; // Immutable array
}

// Use type for unions, intersections, and primitives
type UserId = number;
type Result<T> = Success<T> | Failure;
type JSONValue = string | number | boolean | null | JSONValue[] | { [key: string]: JSONValue };

// Generic types
interface Repository<T> {
  findById(id: number): Promise<T | null>;
  save(entity: T): Promise<void>;
  delete(id: number): Promise<void>;
}

// Utility types (use built-in ones)
type UserUpdate = Partial<User>; // All properties optional
type UserSummary = Pick<User, 'id' | 'email'>; // Only id and email
type UserWithoutPassword = Omit<User, 'password'>; // All except password
type ReadonlyUser = Readonly<User>; // All properties readonly

// Discriminated unions for type-safe states
type LoadingState = { status: 'loading' };
type SuccessState<T> = { status: 'success'; data: T };
type ErrorState = { status: 'error'; error: Error };
type AsyncState<T> = LoadingState | SuccessState<T> | ErrorState;

function handleState<T>(state: AsyncState<T>) {
  switch (state.status) {
    case 'loading':
      console.log('Loading...');
      break;
    case 'success':
      console.log('Data:', state.data); // TypeScript knows data exists
      break;
    case 'error':
      console.error('Error:', state.error); // TypeScript knows error exists
      break;
  }
}

// Type guards
function isUser(obj: unknown): obj is User {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    typeof obj.id === 'number' &&
    'email' in obj &&
    typeof obj.email === 'string'
  );
}

// Assertion functions (TypeScript 3.7+)
function assertIsUser(obj: unknown): asserts obj is User {
  if (!isUser(obj)) {
    throw new Error('Not a valid user');
  }
}

const data: unknown = fetchData();
assertIsUser(data);
// After this point, TypeScript knows data is User
console.log(data.email);
```

## Modern TypeScript Features

```typescript
// Optional chaining (?.)
const userName = user?.profile?.name ?? 'Anonymous';

// Nullish coalescing (??)
const timeout = config.timeout ?? 5000; // Only null/undefined, not 0 or ''

// Template literal types (TypeScript 4.1+)
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';
type Endpoint = `/api/${string}`;
type Route = `${HttpMethod} ${Endpoint}`;

const route: Route = 'GET /api/users'; // Valid
// const invalid: Route = 'INVALID /api/users'; // Error

// Const assertions
const config = {
  timeout: 5000,
  retries: 3
} as const;

// config.timeout = 10000; // Error: readonly

// Tuple types with labels
type Point = [x: number, y: number];
type RGB = [red: number, green: number, blue: number];

// Variadic tuple types (TypeScript 4.0+)
type Prepend<T extends unknown[], U> = [U, ...T];
type Append<T extends unknown[], U> = [...T, U];

// Recursive types (TypeScript 4.1+)
type JSONValue = 
  | string 
  | number 
  | boolean 
  | null 
  | JSONValue[] 
  | { [key: string]: JSONValue };

// Mapped types
type ReadonlyUser = {
  readonly [K in keyof User]: User[K];
};

// Conditional types
type IsString<T> = T extends string ? true : false;
type NonNullable<T> = T extends null | undefined ? never : T;
```

## Project Structure

```
project/
├── package.json
├── tsconfig.json
├── .eslintrc.js
├── .prettierrc
├── README.md
├── src/
│   ├── index.ts
│   ├── models/
│   │   └── user.ts
│   ├── services/
│   │   └── user-service.ts
│   ├── repositories/
│   │   └── user-repository.ts
│   ├── controllers/
│   │   └── users-controller.ts
│   ├── middleware/
│   │   └── auth.ts
│   ├── utils/
│   │   └── validators.ts
│   └── types/
│       ├── index.ts          # Re-export all types
│       └── express.d.ts      # Type declarations/augmentations
├── tests/
│   ├── unit/
│   │   └── user-service.test.ts
│   └── integration/
│       └── users-api.test.ts
└── dist/                     # Compiled output
```

## tsconfig.json (Strict Configuration)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    
    // Strict mode (enable all)
    "strict": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitAny": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    
    // Additional checks
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    
    // Module resolution
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node",
    
    // Source maps and declarations
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

## Dependency Injection Pattern

```typescript
// Using dependency injection container (optional)
import { injectable, inject } from 'inversify';

@injectable()
export class UserService {
  constructor(
    @inject('UserRepository') private repository: UserRepository,
    @inject('Logger') private logger: Logger
  ) {}
  
  async getUser(id: number): Promise<User | null> {
    return this.repository.findById(id);
  }
}

// Simple constructor injection (preferred if no DI container)
export class UserService {
  constructor(
    private readonly repository: UserRepository,
    private readonly logger: Logger
  ) {}
  
  async getUser(id: number): Promise<User | null> {
    return this.repository.findById(id);
  }
}
```

## Error Handling

```typescript
// Custom error classes
export class ApplicationError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number = 500,
    public readonly code?: string
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends ApplicationError {
  constructor(message: string, public readonly fields?: Record<string, string>) {
    super(message, 400, 'VALIDATION_ERROR');
  }
}

export class NotFoundError extends ApplicationError {
  constructor(resource: string) {
    super(`${resource} not found`, 404, 'NOT_FOUND');
  }
}

// Proper async error handling
try {
  const result = await riskyOperation();
} catch (error) {
  if (error instanceof ValidationError) {
    logger.error('Validation failed:', error.message);
    throw new BadRequestError(error.message);
  }
  throw error; // Re-throw unexpected errors
}

// Result type pattern (alternative to exceptions)
type Result<T, E = Error> = 
  | { ok: true; value: T }
  | { ok: false; error: E };

async function getUser(id: number): Promise<Result<User>> {
  try {
    const user = await repository.findById(id);
    if (!user) {
      return { ok: false, error: new Error('User not found') };
    }
    return { ok: true, value: user };
  } catch (error) {
    return { ok: false, error: error as Error };
  }
}

// Usage
const result = await getUser(123);
if (result.ok) {
  console.log(result.value.email);
} else {
  console.error(result.error.message);
}
```

## Tools to Use

**Package Management:**
- `npm` - Default package manager
- `pnpm` - Faster alternative
- `yarn` - Another alternative

**Build & Type Checking:**
- `tsc` - TypeScript compiler
- `tsx` - Run TypeScript directly (dev)
- `esbuild` - Fast bundler

**Linting:**
- `eslint` - Code linter
- `@typescript-eslint/eslint-plugin` - TypeScript rules

**Formatting:**
- `prettier` - Code formatter

**Testing:**
- `jest` - Test framework
- `vitest` - Faster alternative
- `@types/jest` - Type definitions

## Quick Commands

```bash
# Type check
npx tsc --noEmit

# Build
npx tsc
npm run build

# Development with watch
npx tsx watch src/index.ts
npm run dev

# Lint and format
npx eslint src/
npx prettier --write src/

# Test
npm test
npm test -- --coverage
```

## Best Practices

1. **Enable strict mode** - Always
2. **Explicit return types** - For all functions
3. **Use interfaces for objects** - Not types
4. **Prefer `readonly`** - For immutable data
5. **Avoid `any`** - Use `unknown` if type is truly unknown
6. **Use `const` over `let`** - Never use `var`
7. **Leverage type guards** - For runtime type checking
8. **Use utility types** - Don't reinvent the wheel

## Anti-Patterns to Avoid

❌ **Using `any`**
```typescript
function process(data: any): any {  // Loses all type safety
  return data;
}
```

✅ **Use `unknown` or generics**
```typescript
function process<T>(data: T): T {
  return data;
}
```

❌ **Type assertions without checking**
```typescript
const user = data as User;  // Dangerous if data isn't actually User
```

✅ **Type guards**
```typescript
if (isUser(data)) {
  // TypeScript knows data is User
  const user = data;
}
```

❌ **Optional properties for required data**
```typescript
interface User {
  id?: number;  // Should this really be optional?
  email?: string;
}
```

✅ **Required properties, separate optional**
```typescript
interface User {
  id: number;
  email: string;
}

interface UserUpdate {
  email?: string;  // Updates can be partial
}
```

❌ **Ignoring compiler errors**
```typescript
// @ts-ignore
const result = someFunction();  // Hiding real problems
```

✅ **Fix the root cause**
```typescript
const result = someFunction() as ExpectedType;  // If truly necessary
// Or better: fix types so this isn't needed
```

## Code Quality Standards

- Line length: 100 characters
- Strict mode: Enabled
- No implicit any: Yes
- No unused variables: Yes (enforced by ESLint)
- Test coverage: >80% overall, >90% for critical paths
- All public functions: Explicit return types
