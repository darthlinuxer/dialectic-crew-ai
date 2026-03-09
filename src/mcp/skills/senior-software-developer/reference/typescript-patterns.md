# TypeScript Code Quality & Patterns

---
**Language:** TypeScript
**Focus:** SOLID principles, type system patterns, TypeScript-specific idioms
---

## SOLID Principles in TypeScript

### Single Responsibility Principle (SRP)

**Bad:**
```typescript
class User {
  id: string;
  email: string;
  name: string;
  
  saveToDatabase(): void {
    // Database logic
    const db = new Database();
    db.save(this);
  }
  
  sendWelcomeEmail(): void {
    // Email logic
    const smtp = new SmtpClient();
    smtp.send(...);
  }
  
  validatePassword(password: string): boolean {
    // Validation logic
    return password.length >= 8;
  }
}
```

**Good:**
```typescript
interface User {
  readonly id: string;
  readonly email: string;
  readonly name: string;
}

interface UserRepository {
  save(user: User): Promise<void>;
  findById(id: string): Promise<User | null>;
}

class DatabaseUserRepository implements UserRepository {
  constructor(private db: Database) {}
  
  async save(user: User): Promise<void> {
    await this.db.insert('users', user);
  }
  
  async findById(id: string): Promise<User | null> {
    return this.db.findOne<User>('users', { id });
  }
}

interface EmailService {
  sendWelcomeEmail(user: User): Promise<void>;
}

interface PasswordValidator {
  validate(password: string): boolean;
}
```

### Open/Closed Principle (OCP)

**Bad:**
```typescript
class PaymentProcessor {
  processPayment(type: string, amount: number): void {
    if (type === 'credit_card') {
      // Credit card logic
    } else if (type === 'paypal') {
      // PayPal logic
    } else if (type === 'crypto') {
      // Had to modify existing code!
    }
  }
}
```

**Good:**
```typescript
interface PaymentMethod {
  process(amount: number): Promise<void>;
}

class CreditCardPayment implements PaymentMethod {
  async process(amount: number): Promise<void> {
    // Credit card logic
  }
}

class PayPalPayment implements PaymentMethod {
  async process(amount: number): Promise<void> {
    // PayPal logic
  }
}

class CryptoPayment implements PaymentMethod {
  async process(amount: number): Promise<void> {
    // Crypto logic - no modification to existing code!
  }
}

class PaymentProcessor {
  constructor(private method: PaymentMethod) {}
  
  async processPayment(amount: number): Promise<void> {
    await this.method.process(amount);
  }
}
```

### Liskov Substitution Principle (LSP)

**Bad:**
```typescript
class Rectangle {
  constructor(
    protected width: number,
    protected height: number
  ) {}
  
  setWidth(width: number): void {
    this.width = width;
  }
  
  setHeight(height: number): void {
    this.height = height;
  }
  
  area(): number {
    return this.width * this.height;
  }
}

class Square extends Rectangle {
  setWidth(width: number): void {
    this.width = width;
    this.height = width; // Violates LSP!
  }
  
  setHeight(height: number): void {
    this.width = height;
    this.height = height; // Violates LSP!
  }
}
```

**Good:**
```typescript
interface Shape {
  area(): number;
}

class Rectangle implements Shape {
  constructor(
    private readonly width: number,
    private readonly height: number
  ) {}
  
  area(): number {
    return this.width * this.height;
  }
}

class Square implements Shape {
  constructor(private readonly side: number) {}
  
  area(): number {
    return this.side * this.side;
  }
}
```

### Interface Segregation Principle (ISP)

**Bad:**
```typescript
interface Worker {
  work(): void;
  eat(): void;
  sleep(): void;
}

class Robot implements Worker {
  work(): void {
    // Works
  }
  
  eat(): void {
    // Robots don't eat - forced to implement!
    throw new Error('Robots don\'t eat');
  }
  
  sleep(): void {
    // Robots don't sleep - forced to implement!
    throw new Error('Robots don\'t sleep');
  }
}
```

**Good:**
```typescript
interface Workable {
  work(): void;
}

interface Eatable {
  eat(): void;
}

interface Sleepable {
  sleep(): void;
}

class Human implements Workable, Eatable, Sleepable {
  work(): void {
    console.log('Working...');
  }
  
  eat(): void {
    console.log('Eating...');
  }
  
  sleep(): void {
    console.log('Sleeping...');
  }
}

class Robot implements Workable {
  work(): void {
    console.log('Working 24/7...');
  }
}
```

### Dependency Inversion Principle (DIP)

**Bad:**
```typescript
class EmailService {
  send(message: string): void {
    // Send email
  }
}

class NotificationService {
  private emailService = new EmailService(); // Tight coupling!
  
  notify(message: string): void {
    this.emailService.send(message);
  }
}
```

**Good:**
```typescript
interface MessageSender {
  send(message: string): Promise<void>;
}

class EmailService implements MessageSender {
  async send(message: string): Promise<void> {
    // Send email
  }
}

class SmsService implements MessageSender {
  async send(message: string): Promise<void> {
    // Send SMS
  }
}

class NotificationService {
  constructor(private sender: MessageSender) {} // Depends on abstraction
  
  async notify(message: string): Promise<void> {
    await this.sender.send(message);
  }
}
```

## TypeScript-Specific Patterns

### Branded Types (Nominal Typing)

```typescript
// Prevent mixing similar types
type UserId = string & { readonly __brand: 'UserId' };
type ProductId = string & { readonly __brand: 'ProductId' };

function createUserId(id: string): UserId {
  return id as UserId;
}

function createProductId(id: string): ProductId {
  return id as ProductId;
}

function getUser(id: UserId): User {
  // Only UserId allowed, not ProductId
  return users[id];
}

const userId = createUserId('user-123');
const productId = createProductId('prod-456');

getUser(userId); // ✓ OK
// getUser(productId); // ✗ Type error!
```

### Discriminated Unions

```typescript
type LoadingState = {
  status: 'loading';
};

type SuccessState<T> = {
  status: 'success';
  data: T;
};

type ErrorState = {
  status: 'error';
  error: Error;
};

type AsyncState<T> = LoadingState | SuccessState<T> | ErrorState;

function handleState<T>(state: AsyncState<T>): void {
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
```

### Builder Pattern with Fluent API

```typescript
class QueryBuilder {
  private filters: string[] = [];
  private sortFields: string[] = [];
  private limitValue?: number;
  
  where(field: string, value: any): this {
    this.filters.push(`${field} = ${value}`);
    return this;
  }
  
  orderBy(field: string, direction: 'asc' | 'desc' = 'asc'): this {
    this.sortFields.push(`${field} ${direction}`);
    return this;
  }
  
  limit(count: number): this {
    this.limitValue = count;
    return this;
  }
  
  build(): string {
    let query = 'SELECT * FROM table';
    
    if (this.filters.length > 0) {
      query += ` WHERE ${this.filters.join(' AND ')}`;
    }
    
    if (this.sortFields.length > 0) {
      query += ` ORDER BY ${this.sortFields.join(', ')}`;
    }
    
    if (this.limitValue) {
      query += ` LIMIT ${this.limitValue}`;
    }
    
    return query;
  }
}

// Usage
const query = new QueryBuilder()
  .where('status', 'active')
  .where('age', 18)
  .orderBy('name', 'asc')
  .limit(10)
  .build();
```

### Factory Pattern with Type Guards

```typescript
interface Dog {
  type: 'dog';
  bark(): void;
}

interface Cat {
  type: 'cat';
  meow(): void;
}

type Animal = Dog | Cat;

// Type guard
function isDog(animal: Animal): animal is Dog {
  return animal.type === 'dog';
}

function isCat(animal: Animal): animal is Cat {
  return animal.type === 'cat';
}

// Factory
class AnimalFactory {
  static create(type: 'dog'): Dog;
  static create(type: 'cat'): Cat;
  static create(type: Animal['type']): Animal {
    switch (type) {
      case 'dog':
        return {
          type: 'dog',
          bark: () => console.log('Woof!')
        };
      case 'cat':
        return {
          type: 'cat',
          meow: () => console.log('Meow!')
        };
    }
  }
}

// Usage
const dog = AnimalFactory.create('dog');
dog.bark(); // TypeScript knows this is Dog
```

### Singleton Pattern

```typescript
class DatabaseConnection {
  private static instance: DatabaseConnection;
  private connected = false;
  
  private constructor() {
    // Private constructor prevents instantiation
  }
  
  static getInstance(): DatabaseConnection {
    if (!DatabaseConnection.instance) {
      DatabaseConnection.instance = new DatabaseConnection();
    }
    return DatabaseConnection.instance;
  }
  
  connect(): void {
    if (!this.connected) {
      console.log('Connecting to database...');
      this.connected = true;
    }
  }
}

// Usage
const db1 = DatabaseConnection.getInstance();
const db2 = DatabaseConnection.getInstance();
console.log(db1 === db2); // true
```

## Anti-Patterns to Avoid

### Any Type Overuse

**Bad:**
```typescript
function processData(data: any): any {
  // Loses all type safety
  return data.map((item: any) => item.value);
}
```

**Good:**
```typescript
interface DataItem {
  value: number;
}

function processData<T extends DataItem>(data: T[]): number[] {
  return data.map(item => item.value);
}

// Or use unknown if type is truly unknown
function processUnknown(data: unknown): number[] {
  if (!Array.isArray(data)) {
    throw new Error('Data must be an array');
  }
  
  return data.map(item => {
    if (typeof item !== 'object' || item === null || !('value' in item)) {
      throw new Error('Invalid item');
    }
    return (item as DataItem).value;
  });
}
```

### Type Assertions Without Validation

**Bad:**
```typescript
const user = data as User; // Dangerous if data isn't actually User
user.email.toLowerCase(); // Could crash if email is undefined
```

**Good:**
```typescript
function isUser(obj: unknown): obj is User {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    typeof obj.id === 'string' &&
    'email' in obj &&
    typeof obj.email === 'string'
  );
}

if (isUser(data)) {
  // TypeScript knows data is User
  const user = data;
  user.email.toLowerCase(); // Safe
}
```

### Primitive Obsession

**Bad:**
```typescript
function processOrder(
  orderId: string,
  customerId: string,
  items: string[],
  total: number,
  currency: string
): void {
  // Using primitives everywhere
}
```

**Good:**
```typescript
type OrderId = string & { readonly __brand: 'OrderId' };
type CustomerId = string & { readonly __brand: 'CustomerId' };

interface Money {
  readonly amount: number;
  readonly currency: string;
}

interface OrderItem {
  readonly name: string;
  readonly price: Money;
  readonly quantity: number;
}

interface Order {
  readonly id: OrderId;
  readonly customerId: CustomerId;
  readonly items: readonly OrderItem[];
  readonly total: Money;
}

function processOrder(order: Order): void {
  // Type-safe, self-documenting
}
```

### Magic Numbers/Strings

**Bad:**
```typescript
if (user.status === 2) { // What is 2?
}

if (response.code === 'ERR_TIMEOUT') { // Magic string
}
```

**Good:**
```typescript
enum UserStatus {
  Active = 1,
  Suspended = 2,
  Deleted = 3
}

const ErrorCodes = {
  Timeout: 'ERR_TIMEOUT',
  NotFound: 'ERR_NOT_FOUND',
  Unauthorized: 'ERR_UNAUTHORIZED'
} as const;

type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];

if (user.status === UserStatus.Suspended) {
}

if (response.code === ErrorCodes.Timeout) {
}
```

## Error Handling Patterns

### Result Type Pattern

```typescript
type Result<T, E = Error> = 
  | { ok: true; value: T }
  | { ok: false; error: E };

async function fetchUser(id: string): Promise<Result<User>> {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) {
      return { ok: false, error: new Error(`HTTP ${response.status}`) };
    }
    const user = await response.json();
    return { ok: true, value: user };
  } catch (error) {
    return { ok: false, error: error as Error };
  }
}

// Usage
const result = await fetchUser('123');
if (result.ok) {
  console.log(result.value.name);
} else {
  console.error(result.error.message);
}
```

### Custom Error Classes

```typescript
class ApplicationError extends Error {
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

class ValidationError extends ApplicationError {
  constructor(
    message: string,
    public readonly fields?: Record<string, string>
  ) {
    super(message, 400, 'VALIDATION_ERROR');
  }
}

class NotFoundError extends ApplicationError {
  constructor(resource: string) {
    super(`${resource} not found`, 404, 'NOT_FOUND');
  }
}

// Usage
try {
  const user = await getUserById(id);
} catch (error) {
  if (error instanceof NotFoundError) {
    return { status: 404, body: { error: error.message } };
  }
  if (error instanceof ValidationError) {
    return { status: 400, body: { error: error.message, fields: error.fields } };
  }
  throw error;
}
```

### Retry with Exponential Backoff

```typescript
async function retry<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    delayMs?: number;
    backoff?: 'linear' | 'exponential';
  } = {}
): Promise<T> {
  const { maxRetries = 3, delayMs = 1000, backoff = 'exponential' } = options;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
      
      const delay = backoff === 'exponential'
        ? delayMs * Math.pow(2, attempt)
        : delayMs * (attempt + 1);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw new Error('Max retries reached');
}

// Usage
const data = await retry(
  () => fetch('
  { maxRetries: 3, delayMs: 1000, backoff: 'exponential' }
);
```

## Advanced Type Patterns

### Conditional Types

```typescript
type IsString<T> = T extends string ? true : false;
type NonNullable<T> = T extends null | undefined ? never : T;

// Unwrap Promise type
type Awaited<T> = T extends Promise<infer U> ? U : T;

type UserPromise = Promise<User>;
type UnwrappedUser = Awaited<UserPromise>; // User
```

### Mapped Types

```typescript
type ReadonlyUser = {
  readonly [K in keyof User]: User[K];
};

type PartialUser = {
  [K in keyof User]?: User[K];
};

// Make specific properties optional
type OptionalEmail<T> = Omit<T, 'email'> & { email?: string };
```

### Template Literal Types

```typescript
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';
type Endpoint = `/api/${string}`;
type Route = `${HttpMethod} ${Endpoint}`;

const route: Route = 'GET /api/users'; // ✓ Valid
// const invalid: Route = 'INVALID /api/users'; // ✗ Error
```

## Best Practices

1. **Enable strict mode** - Always
2. **Use interfaces for objects** - Types for unions/intersections
3. **Explicit return types** - For all functions
4. **Use `readonly`** - For immutable data
5. **Avoid `any`** - Use `unknown` or generics
6. **Use branded types** - For IDs and similar values
7. **Discriminated unions** - For state management
8. **Type guards** - For runtime type checking
9. **Generics** - For reusable code
10. **Utility types** - Use built-in ones (Partial, Pick, Omit, etc.)
