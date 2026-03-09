# C# Code Quality & Patterns

---
**Language:** C#
**Focus:** SOLID principles, .NET patterns, modern C# idioms
---

## SOLID Principles in C#

### Single Responsibility Principle (SRP)

**Bad:**
```csharp
public class User
{
    public int Id { get; set; }
    public string Email { get; set; }
    public string Name { get; set; }
    
    public void SaveToDatabase()
    {
        // Database logic
        using var connection = new SqlConnection("...");
        // ...
    }
    
    public void SendWelcomeEmail()
    {
        // Email logic
        var smtp = new SmtpClient();
        // ...
    }
    
    public bool ValidatePassword(string password)
    {
        // Validation logic
        return password.Length >= 8;
    }
}
```

**Good:**
```csharp
public record User(int Id, string Email, string Name)
{
    public bool IsAdmin => Email.EndsWith("@admin.com");
}

public interface IUserRepository
{
    Task SaveAsync(User user, CancellationToken ct = default);
    Task<User?> FindByIdAsync(int id, CancellationToken ct = default);
}

public class UserRepository : IUserRepository
{
    private readonly AppDbContext _context;
    
    public UserRepository(AppDbContext context)
    {
        _context = context;
    }
    
    public async Task SaveAsync(User user, CancellationToken ct = default)
    {
        _context.Users.Add(user);
        await _context.SaveChangesAsync(ct);
    }
    
    public async Task<User?> FindByIdAsync(int id, CancellationToken ct = default)
    {
        return await _context.Users.FindAsync(new object[] { id }, ct);
    }
}

public interface IEmailService
{
    Task SendWelcomeEmailAsync(User user, CancellationToken ct = default);
}

public interface IPasswordValidator
{
    bool Validate(string password);
}
```

### Open/Closed Principle (OCP)

**Bad:**
```csharp
public class PaymentProcessor
{
    public void ProcessPayment(string paymentType, decimal amount)
    {
        if (paymentType == "CreditCard")
        {
            // Credit card logic
        }
        else if (paymentType == "PayPal")
        {
            // PayPal logic
        }
        else if (paymentType == "Crypto")
        {
            // Had to modify existing code!
        }
    }
}
```

**Good:**
```csharp
public interface IPaymentMethod
{
    Task ProcessAsync(decimal amount, CancellationToken ct = default);
}

public class CreditCardPayment : IPaymentMethod
{
    public async Task ProcessAsync(decimal amount, CancellationToken ct = default)
    {
        // Credit card logic
        await Task.CompletedTask;
    }
}

public class PayPalPayment : IPaymentMethod
{
    public async Task ProcessAsync(decimal amount, CancellationToken ct = default)
    {
        // PayPal logic
        await Task.CompletedTask;
    }
}

public class CryptoPayment : IPaymentMethod
{
    public async Task ProcessAsync(decimal amount, CancellationToken ct = default)
    {
        // Crypto logic - no modification to existing code!
        await Task.CompletedTask;
    }
}

public class PaymentProcessor
{
    private readonly IPaymentMethod _method;
    
    public PaymentProcessor(IPaymentMethod method)
    {
        _method = method;
    }
    
    public async Task ProcessPaymentAsync(decimal amount, CancellationToken ct = default)
    {
        await _method.ProcessAsync(amount, ct);
    }
}
```

### Liskov Substitution Principle (LSP)

**Bad:**
```csharp
public class Rectangle
{
    public virtual int Width { get; set; }
    public virtual int Height { get; set; }
    
    public int Area() => Width * Height;
}

public class Square : Rectangle
{
    public override int Width
    {
        get => base.Width;
        set
        {
            base.Width = value;
            base.Height = value; // Violates LSP!
        }
    }
    
    public override int Height
    {
        get => base.Height;
        set
        {
            base.Width = value;
            base.Height = value; // Violates LSP!
        }
    }
}
```

**Good:**
```csharp
public interface IShape
{
    int Area();
}

public class Rectangle : IShape
{
    public int Width { get; init; }
    public int Height { get; init; }
    
    public int Area() => Width * Height;
}

public class Square : IShape
{
    public int Side { get; init; }
    
    public int Area() => Side * Side;
}
```

### Interface Segregation Principle (ISP)

**Bad:**
```csharp
public interface IWorker
{
    void Work();
    void Eat();
    void Sleep();
}

public class Robot : IWorker
{
    public void Work()
    {
        // Works
    }
    
    public void Eat()
    {
        // Robots don't eat - forced to implement!
        throw new NotSupportedException("Robots don't eat");
    }
    
    public void Sleep()
    {
        // Robots don't sleep - forced to implement!
        throw new NotSupportedException("Robots don't sleep");
    }
}
```

**Good:**
```csharp
public interface IWorkable
{
    void Work();
}

public interface IEatable
{
    void Eat();
}

public interface ISleepable
{
    void Sleep();
}

public class Human : IWorkable, IEatable, ISleepable
{
    public void Work() => Console.WriteLine("Working...");
    public void Eat() => Console.WriteLine("Eating...");
    public void Sleep() => Console.WriteLine("Sleeping...");
}

public class Robot : IWorkable
{
    public void Work() => Console.WriteLine("Working 24/7...");
}
```

### Dependency Inversion Principle (DIP)

**Bad:**
```csharp
public class EmailService
{
    public void Send(string message)
    {
        // Send email
    }
}

public class NotificationService
{
    private readonly EmailService _emailService = new(); // Tight coupling!
    
    public void Notify(string message)
    {
        _emailService.Send(message);
    }
}
```

**Good:**
```csharp
public interface IMessageSender
{
    Task SendAsync(string message, CancellationToken ct = default);
}

public class EmailService : IMessageSender
{
    public async Task SendAsync(string message, CancellationToken ct = default)
    {
        // Send email
        await Task.CompletedTask;
    }
}

public class SmsService : IMessageSender
{
    public async Task SendAsync(string message, CancellationToken ct = default)
    {
        // Send SMS
        await Task.CompletedTask;
    }
}

public class NotificationService
{
    private readonly IMessageSender _sender;
    
    public NotificationService(IMessageSender sender)
    {
        _sender = sender; // Depends on abstraction
    }
    
    public async Task NotifyAsync(string message, CancellationToken ct = default)
    {
        await _sender.SendAsync(message, ct);
    }
}
```

## Modern C# Design Patterns

### Factory Pattern

```csharp
public enum DatabaseType
{
    Postgres,
    MySql,
    MongoDb
}

public interface IDatabase
{
    Task ConnectAsync(CancellationToken ct = default);
    Task<IEnumerable<object>> ExecuteAsync(string query, CancellationToken ct = default);
}

public class PostgresDatabase : IDatabase
{
    public Task ConnectAsync(CancellationToken ct = default)
    {
        Console.WriteLine("Connecting to PostgreSQL");
        return Task.CompletedTask;
    }
    
    public Task<IEnumerable<object>> ExecuteAsync(string query, CancellationToken ct = default)
    {
        return Task.FromResult(Enumerable.Empty<object>());
    }
}

public class MySqlDatabase : IDatabase
{
    public Task ConnectAsync(CancellationToken ct = default)
    {
        Console.WriteLine("Connecting to MySQL");
        return Task.CompletedTask;
    }
    
    public Task<IEnumerable<object>> ExecuteAsync(string query, CancellationToken ct = default)
    {
        return Task.FromResult(Enumerable.Empty<object>());
    }
}

public static class DatabaseFactory
{
    public static IDatabase Create(DatabaseType type, IConfiguration config)
    {
        return type switch
        {
            DatabaseType.Postgres => new PostgresDatabase(),
            DatabaseType.MySql => new MySqlDatabase(),
            _ => throw new ArgumentException($"Unknown database type: {type}")
        };
    }
}
```

### Strategy Pattern

```csharp
public interface ISortStrategy<T> where T : IComparable<T>
{
    IEnumerable<T> Sort(IEnumerable<T> data);
}

public class QuickSort<T> : ISortStrategy<T> where T : IComparable<T>
{
    public IEnumerable<T> Sort(IEnumerable<T> data)
    {
        var list = data.ToList();
        if (list.Count <= 1) return list;
        
        var pivot = list[list.Count / 2];
        var left = list.Where(x => x.CompareTo(pivot) < 0);
        var middle = list.Where(x => x.CompareTo(pivot) == 0);
        var right = list.Where(x => x.CompareTo(pivot) > 0);
        
        return Sort(left).Concat(middle).Concat(Sort(right));
    }
}

public class BubbleSort<T> : ISortStrategy<T> where T : IComparable<T>
{
    public IEnumerable<T> Sort(IEnumerable<T> data)
    {
        var arr = data.ToArray();
        int n = arr.Length;
        
        for (int i = 0; i < n - 1; i++)
        {
            for (int j = 0; j < n - i - 1; j++)
            {
                if (arr[j].CompareTo(arr[j + 1]) > 0)
                {
                    (arr[j], arr[j + 1]) = (arr[j + 1], arr[j]);
                }
            }
        }
        
        return arr;
    }
}

public class Sorter<T> where T : IComparable<T>
{
    private readonly ISortStrategy<T> _strategy;
    
    public Sorter(ISortStrategy<T> strategy)
    {
        _strategy = strategy;
    }
    
    public IEnumerable<T> Sort(IEnumerable<T> data)
    {
        return _strategy.Sort(data);
    }
}
```

### Disposable Pattern (IDisposable)

```csharp
public class DatabaseConnection : IDisposable
{
    private SqlConnection? _connection;
    private bool _disposed;
    
    public void Connect()
    {
        _connection = new SqlConnection("...");
        _connection.Open();
    }
    
    public void Dispose()
    {
        Dispose(disposing: true);
        GC.SuppressFinalize(this);
    }
    
    protected virtual void Dispose(bool disposing)
    {
        if (!_disposed)
        {
            if (disposing)
            {
                // Dispose managed resources
                _connection?.Close();
                _connection?.Dispose();
            }
            
            // Free unmanaged resources
            
            _disposed = true;
        }
    }
    
    ~DatabaseConnection()
    {
        Dispose(disposing: false);
    }
}

// Modern async disposal
public class AsyncDatabaseConnection : IAsyncDisposable
{
    private SqlConnection? _connection;
    
    public async ValueTask DisposeAsync()
    {
        if (_connection is not null)
        {
            await _connection.CloseAsync();
            await _connection.DisposeAsync();
        }
        
        GC.SuppressFinalize(this);
    }
}
```

### Options Pattern

```csharp
public class EmailOptions
{
    public const string SectionName = "Email";
    
    public string SmtpServer { get; set; } = string.Empty;
    public int Port { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}

// In Program.cs
builder.Services.Configure<EmailOptions>(
    builder.Configuration.GetSection(EmailOptions.SectionName));

// In service
public class EmailService
{
    private readonly EmailOptions _options;
    
    public EmailService(IOptions<EmailOptions> options)
    {
        _options = options.Value;
    }
    
    public async Task SendAsync(string to, string message)
    {
        // Use _options.SmtpServer, etc.
    }
}
```

## Anti-Patterns to Avoid

### God Object

**Bad:**
```csharp
public class Application
{
    public void ConnectToDatabase() { }
    public void SendEmail() { }
    public void ProcessPayment() { }
    public void GenerateReport() { }
    public void AuthenticateUser() { }
    // ... 50 more methods - does everything!
}
```

**Good:**
```csharp
public class DatabaseService
{
    public Task ConnectAsync(CancellationToken ct = default) => Task.CompletedTask;
}

public class EmailService
{
    public Task SendAsync(string to, string message, CancellationToken ct = default) 
        => Task.CompletedTask;
}

public class PaymentService
{
    public Task ProcessAsync(decimal amount, CancellationToken ct = default) 
        => Task.CompletedTask;
}

public class ReportGenerator
{
    public Task GenerateAsync(object data, CancellationToken ct = default) 
        => Task.CompletedTask;
}

public class AuthenticationService
{
    public Task<bool> AuthenticateAsync(string credentials, CancellationToken ct = default) 
        => Task.FromResult(true);
}
```

### Primitive Obsession

**Bad:**
```csharp
public void ProcessOrder(
    string orderId,
    string customerId,
    List<string> items,
    decimal total,
    string currency)
{
    // Using primitives everywhere
}
```

**Good:**
```csharp
public readonly record struct OrderId(Guid Value);
public readonly record struct CustomerId(Guid Value);

public record Money(decimal Amount, string Currency)
{
    public Money
    {
        if (Amount < 0)
            throw new ArgumentException("Amount cannot be negative", nameof(Amount));
    }
}

public record OrderItem(string Name, Money Price, int Quantity);

public record Order(
    OrderId Id,
    CustomerId CustomerId,
    IReadOnlyList<OrderItem> Items,
    Money Total);

public void ProcessOrder(Order order)
{
    // Type-safe, self-documenting
}
```

### Magic Numbers/Strings

**Bad:**
```csharp
if (user.Status == 2) // What is 2?
{
}

if (response.Code == "ERR_TIMEOUT") // Magic string
{
}
```

**Good:**
```csharp
public enum UserStatus
{
    Active = 1,
    Suspended = 2,
    Deleted = 3
}

public static class ErrorCodes
{
    public const string Timeout = "ERR_TIMEOUT";
    public const string NotFound = "ERR_NOT_FOUND";
    public const string Unauthorized = "ERR_UNAUTHORIZED";
}

if (user.Status == UserStatus.Suspended)
{
}

if (response.Code == ErrorCodes.Timeout)
{
}
```

### Leaky Abstraction

**Bad:**
```csharp
public interface IUserRepository
{
    User GetUserWithSql(int userId); // Leaks implementation detail
}
```

**Good:**
```csharp
public interface IUserRepository
{
    Task<User?> FindByIdAsync(int userId, CancellationToken ct = default);
    // Implementation hidden, can change to NoSQL without breaking interface
}
```

## Error Handling Patterns

### Result Type Pattern

```csharp
public readonly record struct Result<T, TError>
{
    public bool IsSuccess { get; }
    public T? Value { get; }
    public TError? Error { get; }
    
    private Result(T value)
    {
        IsSuccess = true;
        Value = value;
        Error = default;
    }
    
    private Result(TError error)
    {
        IsSuccess = false;
        Value = default;
        Error = error;
    }
    
    public static Result<T, TError> Success(T value) => new(value);
    public static Result<T, TError> Failure(TError error) => new(error);
    
    public TResult Match<TResult>(
        Func<T, TResult> onSuccess,
        Func<TError, TResult> onFailure)
    {
        return IsSuccess ? onSuccess(Value!) : onFailure(Error!);
    }
}

// Usage
public async Task<Result<User, string>> FetchUserAsync(int id)
{
    try
    {
        var user = await _api.GetAsync($"/users/{id}");
        return Result<User, string>.Success(user);
    }
    catch (Exception ex)
    {
        return Result<User, string>.Failure(ex.Message);
    }
}

var result = await FetchUserAsync(123);
var output = result.Match(
    onSuccess: user => $"Found: {user.Name}",
    onFailure: error => $"Error: {error}"
);
```

### Custom Exception Hierarchy

```csharp
public class ApplicationException : Exception
{
    public string Code { get; }
    
    public ApplicationException(string message, string code, Exception? innerException = null)
        : base(message, innerException)
    {
        Code = code;
    }
}

public class ValidationException : ApplicationException
{
    public IReadOnlyDictionary<string, string[]> Errors { get; }
    
    public ValidationException(
        string message,
        IReadOnlyDictionary<string, string[]> errors)
        : base(message, "VALIDATION_ERROR")
    {
        Errors = errors;
    }
}

public class NotFoundException : ApplicationException
{
    public NotFoundException(string resource)
        : base($"{resource} not found", "NOT_FOUND")
    {
    }
}

public class UnauthorizedException : ApplicationException
{
    public UnauthorizedException(string message = "Unauthorized")
        : base(message, "UNAUTHORIZED")
    {
    }
}

// Usage
try
{
    var user = await GetUserAsync(userId);
}
catch (NotFoundException)
{
    return Results.NotFound(new { Error = "User not found" });
}
catch (UnauthorizedException)
{
    return Results.Unauthorized();
}
catch (ApplicationException ex)
{
    return Results.Problem(ex.Message);
}
```

### Retry with Polly

```csharp
// Install: Polly
using Polly;
using Polly.Retry;

public class ResilientHttpClient
{
    private readonly HttpClient _httpClient;
    private readonly AsyncRetryPolicy<HttpResponseMessage> _retryPolicy;
    
    public ResilientHttpClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
        
        _retryPolicy = Policy
            .HandleResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
            .Or<HttpRequestException>()
            .WaitAndRetryAsync(
                retryCount: 3,
                sleepDurationProvider: attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt)),
                onRetry: (outcome, timespan, attempt, context) =>
                {
                    Console.WriteLine($"Retry {attempt} after {timespan.TotalSeconds}s");
                });
    }
    
    public async Task<HttpResponseMessage> GetAsync(string url, CancellationToken ct = default)
    {
        return await _retryPolicy.ExecuteAsync(() => _httpClient.GetAsync(url, ct));
    }
}
```

## Performance Patterns

### N+1 Query Problem

**Bad:**
```csharp
// 1 query to get users, then N queries for their orders
var users = await _context.Users.ToListAsync(); // 1 query
foreach (var user in users)
{
    var orders = await _context.Orders
        .Where(o => o.UserId == user.Id)
        .ToListAsync(); // N queries!
}
```

**Good:**
```csharp
// 1 query with eager loading
var users = await _context.Users
    .Include(u => u.Orders)
    .ToListAsync();
```

### Caching with MemoryCache

```csharp
public class CachedUserRepository
{
    private readonly IUserRepository _repository;
    private readonly IMemoryCache _cache;
    
    public CachedUserRepository(IUserRepository repository, IMemoryCache cache)
    {
        _repository = repository;
        _cache = cache;
    }
    
    public async Task<User?> GetUserAsync(int id, CancellationToken ct = default)
    {
        var cacheKey = $"user:{id}";
        
        if (_cache.TryGetValue(cacheKey, out User? cachedUser))
        {
            return cachedUser;
        }
        
        var user = await _repository.FindByIdAsync(id, ct);
        
        if (user is not null)
        {
            _cache.Set(cacheKey, user, TimeSpan.FromMinutes(5));
        }
        
        return user;
    }
    
    public void InvalidateCache(int id)
    {
        _cache.Remove($"user:{id}");
    }
}
```

## Best Practices

1. **Use records** for immutable data
2. **Use nullable reference types** (`string?`)
3. **Use async/await** properly
4. **Prefer interfaces** over abstract classes
5. **Use dependency injection**
6. **Follow naming conventions** (PascalCase for public, camelCase for private)
7. **Use file-scoped namespaces** in .NET 6+
8. **Use pattern matching**
9. **Use `CancellationToken`** for async methods
10. **Dispose resources** properly (IDisposable, using statements)
