# Node.js Best Practices

---
**Language:** Node.js (JavaScript/TypeScript runtime)
**Use when:** Building Node.js servers, APIs, CLIs, or backend services
---

## Project Setup

```json
// package.json
{
  "name": "project-name",
  "version": "1.0.0",
  "type": "module",
  "engines": {
    "node": ">=20.0.0"
  },
  "scripts": {
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "test": "jest",
    "test:watch": "jest --watch",
    "lint": "eslint src/**/*.ts",
    "format": "prettier --write src/**/*.ts"
  },
  "dependencies": {
    "fastify": "^4.25.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "tsx": "^4.7.0",
    "@types/node": "^20.10.0",
    "jest": "^29.7.0",
    "eslint": "^8.56.0",
    "prettier": "^3.1.0"
  }
}
```

## Environment Configuration

```typescript
// src/config/environment.ts
import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  REDIS_URL: z.string().url().optional(),
});

export type Environment = z.infer<typeof envSchema>;

export function loadEnvironment(): Environment {
  const parsed = envSchema.safeParse(process.env);
  
  if (!parsed.success) {
    console.error('❌ Invalid environment variables:');
    console.error(parsed.error.format());
    process.exit(1);
  }
  
  return parsed.data;
}

// Usage in main
const env = loadEnvironment(); // Validates on startup
```

## Error Handling

```typescript
// src/errors/index.ts
export class ApplicationError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number = 500,
    public readonly code?: string,
    public readonly isOperational: boolean = true
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

export class UnauthorizedError extends ApplicationError {
  constructor(message: string = 'Unauthorized') {
    super(message, 401, 'UNAUTHORIZED');
  }
}

// Global error handler (Express)
import { Request, Response, NextFunction } from 'express';

export function errorHandler(
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) {
  if (err instanceof ApplicationError) {
    return res.status(err.statusCode).json({
      error: {
        message: err.message,
        code: err.code,
        ...(err instanceof ValidationError && { fields: err.fields })
      }
    });
  }
  
  logger.error('Unexpected error:', err);
  
  return res.status(500).json({
    error: {
      message: 'Internal server error',
      code: 'INTERNAL_ERROR'
    }
  });
}

// Global error handler (Fastify)
import { FastifyError, FastifyReply, FastifyRequest } from 'fastify';

export function fastifyErrorHandler(
  error: FastifyError,
  request: FastifyRequest,
  reply: FastifyReply
) {
  if (error instanceof ApplicationError) {
    return reply.status(error.statusCode).send({
      error: {
        message: error.message,
        code: error.code
      }
    });
  }
  
  logger.error('Unexpected error:', error);
  
  return reply.status(500).send({
    error: {
      message: 'Internal server error',
      code: 'INTERNAL_ERROR'
    }
  });
}
```

## Async Patterns

```typescript
// Promise.all for parallel execution
const [users, posts, comments] = await Promise.all([
  fetchUsers(),
  fetchPosts(),
  fetchComments()
]);

// Promise.allSettled for handling failures gracefully
const results = await Promise.allSettled([
  fetchUsers(),
  fetchPosts(),
  fetchComments()
]);

results.forEach((result, index) => {
  if (result.status === 'fulfilled') {
    console.log(`Task ${index} succeeded:`, result.value);
  } else {
    console.error(`Task ${index} failed:`, result.reason);
  }
});

// Async iteration
for await (const chunk of readStream) {
  await processChunk(chunk);
}

// Abort controller for cancellation
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 5000);

try {
  const response = await fetch(url, { signal: controller.signal });
  return await response.json();
} catch (error) {
  if (error.name === 'AbortError') {
    console.log('Request timed out');
  }
  throw error;
} finally {
  clearTimeout(timeout);
}

// Retry with exponential backoff
async function retry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delayMs: number = 1000
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, delayMs * Math.pow(2, i)));
    }
  }
  throw new Error('Max retries reached');
}
```

## Graceful Shutdown

```typescript
// src/server.ts
import { Server } from 'node:http';

export class GracefulShutdown {
  private server: Server;
  private connections: Set<any> = new Set();
  
  constructor(server: Server) {
    this.server = server;
    
    // Track connections
    server.on('connection', (conn) => {
      this.connections.add(conn);
      conn.on('close', () => this.connections.delete(conn));
    });
    
    // Handle shutdown signals
    process.on('SIGTERM', () => this.shutdown('SIGTERM'));
    process.on('SIGINT', () => this.shutdown('SIGINT'));
  }
  
  private async shutdown(signal: string): Promise<void> {
    console.log(`${signal} received, starting graceful shutdown...`);
    
    // Stop accepting new connections
    this.server.close(() => {
      console.log('Server closed');
    });
    
    // Close existing connections
    for (const conn of this.connections) {
      conn.end();
    }
    
    // Wait for cleanup
    await this.cleanup();
    
    console.log('Graceful shutdown complete');
    process.exit(0);
  }
  
  private async cleanup(): Promise<void> {
    // Close database connections
    // await database.disconnect();
    
    // Close Redis connections
    // await redis.quit();
    
    // Any other cleanup
  }
}

// Usage
const server = app.listen(port);
new GracefulShutdown(server);
```

## Logging

```typescript
// src/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: process.env.NODE_ENV === 'development' 
    ? {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'SYS:standard',
          ignore: 'pid,hostname'
        }
      }
    : undefined
});

// Usage
logger.info('Server started', { port: 3000 });
logger.error('Failed to process request', { error, userId });
logger.debug('Processing data', { data });
```

## Streams for Large Data

```typescript
// Reading large files
import { createReadStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { Transform } from 'node:stream';

async function processLargeFile(filePath: string): Promise<void> {
  const readStream = createReadStream(filePath);
  
  const processStream = new Transform({
    transform(chunk, encoding, callback) {
      // Process each chunk
      const processed = chunk.toString().toUpperCase();
      callback(null, processed);
    }
  });
  
  await pipeline(
    readStream,
    processStream,
    process.stdout
  );
}

// Streaming HTTP responses
import { Readable } from 'node:stream';

app.get('/stream', (req, res) => {
  const stream = Readable.from(async function* () {
    for (let i = 0; i < 1000; i++) {
      yield `data: ${i}\n\n`;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }());
  
  res.setHeader('Content-Type', 'text/event-stream');
  stream.pipe(res);
});
```

## Performance Optimization

```typescript
// Worker threads for CPU-intensive tasks
import { Worker } from 'node:worker_threads';

function runWorker(data: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const worker = new Worker('./worker.js', { workerData: data });
    
    worker.on('message', resolve);
    worker.on('error', reject);
    worker.on('exit', (code) => {
      if (code !== 0) {
        reject(new Error(`Worker stopped with exit code ${code}`));
      }
    });
  });
}

// Cluster for multi-core utilization
import cluster from 'node:cluster';
import { cpus } from 'node:os';

if (cluster.isPrimary) {
  const numCPUs = cpus().length;
  
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }
  
  cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died, starting new worker`);
    cluster.fork();
  });
} else {
  // Start server in worker
  startServer();
}

// Caching with LRU
import LRU from 'lru-cache';

const cache = new LRU<string, any>({
  max: 500,
  ttl: 1000 * 60 * 5, // 5 minutes
});

async function getCachedUser(id: string): Promise<User> {
  const cached = cache.get(id);
  if (cached) return cached;
  
  const user = await fetchUser(id);
  cache.set(id, user);
  return user;
}
```

## Security Best Practices

```typescript
// Helmet for security headers (Express)
import helmet from 'helmet';
app.use(helmet());

// Rate limiting
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});

app.use('/api/', limiter);

// Input validation with Zod
import { z } from 'zod';

const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().min(2).max(50)
});

app.post('/users', async (req, res) => {
  const result = createUserSchema.safeParse(req.body);
  
  if (!result.success) {
    return res.status(400).json({ errors: result.error.errors });
  }
  
  const user = await createUser(result.data);
  res.json(user);
});

// SQL injection prevention (use parameterized queries)
// ❌ Bad
db.query(`SELECT * FROM users WHERE id = ${userId}`);

// ✅ Good
db.query('SELECT * FROM users WHERE id = ?', [userId]);
```

## Tools to Use

**Runtime:**
- `node` - Node.js runtime
- `tsx` - Run TypeScript directly (development)
- `pm2` - Process manager (production)

**Web Frameworks:**
- `fastify` - Fast, low overhead (recommended)
- `express` - Popular, extensive ecosystem
- `hono` - Ultra-fast, edge-ready

**Validation:**
- `zod` - TypeScript-first schema validation

**Database:**
- `prisma` - Modern ORM
- `drizzle` - Lightweight ORM
- `pg` - PostgreSQL client

**Testing:**
- `jest` - Full-featured test framework
- `vitest` - Faster alternative
- `supertest` - HTTP assertions

## Quick Commands

```bash
# Development
npm run dev

# Build
npm run build

# Start production
npm start

# Test
npm test
npm run test:watch

# Lint and format
npm run lint
npm run format

# Production deployment
npm ci
npm run build
NODE_ENV=production npm start
```

## Best Practices

1. **Validate environment at startup** - Fail fast if config is wrong
2. **Use async/await** - Never use callbacks
3. **Implement graceful shutdown** - Clean up resources
4. **Stream large data** - Don't load everything into memory
5. **Use structured logging** - JSON logs for production
6. **Rate limit APIs** - Protect against abuse
7. **Validate all input** - Never trust user data
8. **Use parameterized queries** - Prevent SQL injection
9. **Monitor event loop lag** - Track performance
10. **Cluster for production** - Utilize all CPU cores

## Anti-Patterns to Avoid

❌ **Blocking the event loop**
```typescript
// Bad: Synchronous operations
const data = fs.readFileSync('large-file.txt');
```

✅ **Use async**
```typescript
// Good: Async operations
const data = await fs.promises.readFile('large-file.txt');
```

❌ **Unhandled promise rejections**
```typescript
// Bad: No error handling
doSomethingAsync();
```

✅ **Handle errors**
```typescript
// Good: Proper error handling
try {
  await doSomethingAsync();
} catch (error) {
  logger.error('Operation failed', { error });
}

// Or at process level
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection', { reason, promise });
  process.exit(1);
});
```

❌ **Not cleaning up resources**
```typescript
// Bad: Server keeps running
process.exit(0);
```

✅ **Graceful shutdown**
```typescript
// Good: Clean up first
process.on('SIGTERM', async () => {
  await server.close();
  await database.disconnect();
  process.exit(0);
});
```

## Code Quality Standards

- ES modules: Use `import/export`, not `require`
- Async operations: Always use async/await
- Error handling: Global handlers + try/catch
- Logging: Structured JSON logs
- Environment: Validate on startup
- Shutdown: Implement graceful shutdown
- Security: Helmet, rate limiting, input validation
