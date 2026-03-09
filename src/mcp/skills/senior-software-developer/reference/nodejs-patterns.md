# Node.js Code Quality & Patterns

---
**Language:** Node.js (JavaScript/TypeScript runtime)
**Focus:** Async patterns, error handling, performance, Node.js-specific idioms
---

## Async Patterns

### Promise.all for Parallel Execution

**Bad:**
```javascript
// Sequential - slow!
const user = await fetchUser(id);
const posts = await fetchPosts(id);
const comments = await fetchComments(id);
// Total time: sum of all requests
```

**Good:**
```javascript
// Parallel - fast!
const [user, posts, comments] = await Promise.all([
  fetchUser(id),
  fetchPosts(id),
  fetchComments(id)
]);
// Total time: longest single request
```

### Promise.allSettled for Handling Failures Gracefully

```javascript
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
```

### Async Iteration

```javascript
import { createReadStream } from 'fs';
import { createInterface } from 'readline';

async function processLargeFile(filePath) {
  const fileStream = createReadStream(filePath);
  const rl = createInterface({
    input: fileStream,
    crlfDelay: Infinity
  });
  
  for await (const line of rl) {
    await processLine(line);
  }
}

// Async generators
async function* generateData() {
  for (let i = 0; i < 1000; i++) {
    await new Promise(resolve => setTimeout(resolve, 10));
    yield i;
  }
}

for await (const value of generateData()) {
  console.log(value);
}
```

### Abort Controller for Cancellation

```javascript
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
```

### Retry with Exponential Backoff

```javascript
async function retry(fn, options = {}) {
  const {
    maxRetries = 3,
    delayMs = 1000,
    backoff = 'exponential',
    onRetry = () => {}
  } = options;
  
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
      
      onRetry(attempt + 1, delay, error);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Usage
const data = await retry(
  () => fetch('
  {
    maxRetries: 3,
    delayMs: 1000,
    backoff: 'exponential',
    onRetry: (attempt, delay, error) => {
      console.log(`Retry attempt ${attempt} after ${delay}ms. Error:`, error.message);
    }
  }
);
```

## Error Handling Patterns

### Custom Error Classes

```javascript
class ApplicationError extends Error {
  constructor(message, statusCode = 500, code, isOperational = true) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.code = code;
    this.isOperational = isOperational;
    Error.captureStackTrace(this, this.constructor);
  }
}

class ValidationError extends ApplicationError {
  constructor(message, fields) {
    super(message, 400, 'VALIDATION_ERROR');
    this.fields = fields;
  }
}

class NotFoundError extends ApplicationError {
  constructor(resource) {
    super(`${resource} not found`, 404, 'NOT_FOUND');
  }
}

class UnauthorizedError extends ApplicationError {
  constructor(message = 'Unauthorized') {
    super(message, 401, 'UNAUTHORIZED');
  }
}

// Usage
try {
  const user = await getUserById(id);
} catch (error) {
  if (error instanceof NotFoundError) {
    return res.status(404).json({ error: error.message });
  }
  if (error instanceof ValidationError) {
    return res.status(400).json({
      error: error.message,
      fields: error.fields
    });
  }
  throw error; // Re-throw unexpected errors
}
```

### Global Error Handlers

```javascript
// Express
function errorHandler(err, req, res, next) {
  if (err instanceof ApplicationError) {
    return res.status(err.statusCode).json({
      error: {
        message: err.message,
        code: err.code
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

app.use(errorHandler);

// Fastify
app.setErrorHandler((error, request, reply) => {
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
});

// Process-level handlers
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});
```

### Result Type Pattern

```javascript
function success(value) {
  return { ok: true, value };
}

function failure(error) {
  return { ok: false, error };
}

async function fetchUser(id) {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) {
      return failure(new Error(`HTTP ${response.status}`));
    }
    const user = await response.json();
    return success(user);
  } catch (error) {
    return failure(error);
  }
}

// Usage
const result = await fetchUser(123);
if (result.ok) {
  console.log(result.value.name);
} else {
  console.error(result.error.message);
}
```

## Graceful Shutdown

```javascript
class GracefulShutdown {
  constructor(server) {
    this.server = server;
    this.connections = new Set();
    this.isShuttingDown = false;
    
    // Track connections
    server.on('connection', (conn) => {
      this.connections.add(conn);
      conn.on('close', () => this.connections.delete(conn));
    });
    
    // Handle shutdown signals
    process.on('SIGTERM', () => this.shutdown('SIGTERM'));
    process.on('SIGINT', () => this.shutdown('SIGINT'));
  }
  
  async shutdown(signal) {
    if (this.isShuttingDown) return;
    this.isShuttingDown = true;
    
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
  
  async cleanup() {
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

## Performance Patterns

### Worker Threads for CPU-Intensive Tasks

```javascript
import { Worker } from 'worker_threads';

function runWorker(data) {
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

// worker.js
import { parentPort, workerData } from 'worker_threads';

// CPU-intensive work
const result = heavyComputation(workerData);

parentPort.postMessage(result);
```

### Cluster for Multi-Core Utilization

```javascript
import cluster from 'cluster';
import { cpus } from 'os';
import process from 'process';

if (cluster.isPrimary) {
  const numCPUs = cpus().length;
  
  console.log(`Primary ${process.pid} is running`);
  console.log(`Forking ${numCPUs} workers...`);
  
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }
  
  cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died. Starting new worker...`);
    cluster.fork();
  });
} else {
  // Worker process
  startServer();
  console.log(`Worker ${process.pid} started`);
}
```

### Caching with LRU

```javascript
import LRU from 'lru-cache';

const cache = new LRU({
  max: 500, // Maximum number of items
  ttl: 1000 * 60 * 5, // 5 minutes
  updateAgeOnGet: true,
  updateAgeOnHas: false
});

async function getCachedUser(id) {
  const cached = cache.get(id);
  if (cached) {
    return cached;
  }
  
  const user = await fetchUser(id);
  cache.set(id, user);
  return user;
}

// Invalidate cache
function invalidateCache(id) {
  cache.delete(id);
}
```

### Streams for Large Data

```javascript
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import { Transform } from 'stream';

// Reading large files
async function processLargeFile(inputPath, outputPath) {
  const readStream = createReadStream(inputPath);
  const writeStream = createWriteStream(outputPath);
  
  const processStream = new Transform({
    transform(chunk, encoding, callback) {
      // Process each chunk
      const processed = chunk.toString().toUpperCase();
      callback(null, processed);
    }
  });
  
  await pipeline(readStream, processStream, writeStream);
}

// Streaming HTTP responses
import { Readable } from 'stream';

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

## Security Patterns

### Environment Variable Validation

```javascript
import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  REDIS_URL: z.string().url().optional(),
});

function loadEnvironment() {
  const parsed = envSchema.safeParse(process.env);
  
  if (!parsed.success) {
    console.error('❌ Invalid environment variables:');
    console.error(parsed.error.format());
    process.exit(1);
  }
  
  return parsed.data;
}

// Validate on startup
const env = loadEnvironment();
export { env };
```

### Rate Limiting

```javascript
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});

app.use('/api/', limiter);

// Custom rate limiter per user
const userLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 10,
  keyGenerator: (req) => req.user?.id || req.ip,
  skip: (req) => req.user?.role === 'admin',
});

app.use('/api/users/', userLimiter);
```

### Input Validation with Zod

```javascript
import { z } from 'zod';

const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().min(2).max(50),
  age: z.number().int().positive().optional()
});

app.post('/users', async (req, res) => {
  const result = createUserSchema.safeParse(req.body);
  
  if (!result.success) {
    return res.status(400).json({
      error: 'Validation failed',
      details: result.error.errors
    });
  }
  
  const user = await createUser(result.data);
  res.json(user);
});
```

### SQL Injection Prevention

**Bad:**
```javascript
// ❌ Never do this!
const userId = req.params.id;
db.query(`SELECT * FROM users WHERE id = ${userId}`);
```

**Good:**
```javascript
// ✅ Use parameterized queries
const userId = req.params.id;
db.query('SELECT * FROM users WHERE id = ?', [userId]);

// Or with named parameters
db.query('SELECT * FROM users WHERE id = :id', { id: userId });

// Or with ORM
const user = await User.findByPk(userId);
```

## Logging Patterns

```javascript
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
    : undefined,
  // Add request ID to all logs
  mixin() {
    return { context: 'app' };
  }
});

// Usage
logger.info({ userId: 123 }, 'User logged in');
logger.error({ error, userId: 123 }, 'Failed to process request');
logger.debug({ data }, 'Processing data');

// Request logging middleware
function requestLogger(req, res, next) {
  const start = Date.now();
  
  res.on('finish', () => {
    logger.info({
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration: Date.now() - start,
      ip: req.ip
    }, 'Request completed');
  });
  
  next();
}

app.use(requestLogger);
```

## Anti-Patterns to Avoid

### Blocking the Event Loop

**Bad:**
```javascript
// ❌ Synchronous file I/O
const data = fs.readFileSync('large-file.txt');

// ❌ Synchronous crypto
const hash = crypto.createHash('sha256').update(data).digest('hex');

// ❌ Long synchronous loops
for (let i = 0; i < 1000000; i++) {
  // Heavy computation
}
```

**Good:**
```javascript
// ✅ Async file I/O
const data = await fs.promises.readFile('large-file.txt');

// ✅ Async crypto with worker threads
const hash = await runWorker({ data, algorithm: 'sha256' });

// ✅ Break up long operations
async function processLargeArray(array) {
  for (let i = 0; i < array.length; i++) {
    await processItem(array[i]);
    
    // Yield to event loop every 100 items
    if (i % 100 === 0) {
      await new Promise(resolve => setImmediate(resolve));
    }
  }
}
```

### Not Cleaning Up Resources

**Bad:**
```javascript
// ❌ No cleanup
process.exit(0);
```

**Good:**
```javascript
// ✅ Graceful shutdown
process.on('SIGTERM', async () => {
  await server.close();
  await database.disconnect();
  await redis.quit();
  process.exit(0);
});
```

### Ignoring Errors

**Bad:**
```javascript
// ❌ Silent failure
doSomethingAsync().catch(() => {});

// ❌ No error handling
const result = await riskyOperation();
```

**Good:**
```javascript
// ✅ Handle errors
try {
  const result = await riskyOperation();
} catch (error) {
  logger.error('Operation failed', { error });
  throw new ApplicationError('Failed to process request');
}

// ✅ Process-level handlers
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection', { reason, promise });
  process.exit(1);
});
```

## Best Practices

1. **Validate environment** on startup
2. **Use async/await** everywhere
3. **Implement graceful shutdown**
4. **Stream large data**
5. **Use structured logging**
6. **Rate limit APIs**
7. **Validate all input**
8. **Use parameterized queries**
9. **Monitor event loop lag**
10. **Cluster for production**
11. **Handle errors globally**
12. **Use worker threads** for CPU-intensive tasks
13. **Prefer ES modules** (`import/export`)
14. **Keep dependencies updated**
15. **Use TypeScript** for type safety
