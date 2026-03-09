# C# Style Guide

---
**Language:** C#
**Use when:** Working with C# projects, .NET applications, or ASP.NET Core
---

## Naming Conventions

```csharp
// Namespace: PascalCase
namespace CompanyName.ProductName.Feature
{
    // Interface: PascalCase with 'I' prefix
    public interface IUserRepository
    {
        Task<User> FindByIdAsync(int id);
    }
    
    // Class: PascalCase
    public class UserRepository : IUserRepository
    {
        // Private fields: _camelCase
        private readonly IDatabase _database;
        private readonly ILogger<UserRepository> _logger;
        
        // Public properties: PascalCase
        public int MaxRetries { get; set; }
        
        // Constructor: PascalCase (same as class name)
        public UserRepository(IDatabase database, ILogger<UserRepository> logger)
        {
            _database = database;
            _logger = logger;
        }
        
        // Public methods: PascalCase
        public async Task<User> FindByIdAsync(int id)
        {
            // Local variables: camelCase
            var user = await _database.QueryAsync<User>(id);
            return user;
        }
        
        // Private methods: PascalCase (not _PascalCase)
        private void ValidateInput(int id)
        {
            if (id <= 0)
                throw new ArgumentException("ID must be positive", nameof(id));
        }
    }
    
    // Constants: PascalCase
    public const int MaxRetries = 3;
    
    // Enum: PascalCase
    public enum UserRole
    {
        Standard,
        Admin,
        SuperAdmin
    }
}
```

## Modern C# Features (Use These!)

```csharp
// Record types (C# 9+) for immutable data
public record User(int Id, string Email, DateTime CreatedAt);

// With expressions for creating modified copies
var updatedUser = user with { Email = "newemail@example.com" };

// Init-only properties (C# 9+)
public class Configuration
{
    public string ConnectionString { get; init; }
    public int Timeout { get; init; }
}

var config = new Configuration 
{ 
    ConnectionString = "...",
    Timeout = 30 
};

// Pattern matching (C# 8+)
public decimal GetDiscount(Customer customer) => customer switch
{
    { IsPremium: true } => 0.20m,
    { Orders.Count: > 10 } => 0.10m,
    { MemberSince: var date } when date < DateTime.Now.AddYears(-1) => 0.05m,
    _ => 0m
};

// Nullable reference types (C# 8+) - ALWAYS ENABLE
#nullable enable

public class UserService
{
    // Non-nullable by default
    public string GetUserName(User user)
    {
        return user.Name; // Compiler ensures user is not null
    }
    
    // Explicit nullable
    public User? FindUser(int id)
    {
        return _repository.FindById(id); // May return null
    }
    
    // Null-forgiving operator (use sparingly)
    public void Process()
    {
        var user = GetCurrentUser();
        ProcessUser(user!); // Tell compiler: I know this isn't null
    }
}

// Using declarations (C# 8+)
public async Task ProcessFileAsync(string path)
{
    using var reader = new StreamReader(path); // Disposed at end of scope
    var content = await reader.ReadToEndAsync();
}

// Async streams (C# 8+)
public async IAsyncEnumerable<User> GetUsersAsync()
{
    await foreach (var user in _database.QueryAsync<User>())
    {
        yield return user;
    }
}

// Static using (C# 6+)
using static System.Math;

var result = Sqrt(16) + Pow(2, 3); // No need for Math.Sqrt

// File-scoped namespaces (C# 10+)
namespace CompanyName.ProductName.Feature;

public class UserService
{
    // No extra indentation level!
}

// Global usings (C# 10+) in GlobalUsings.cs
global using System;
global using System.Collections.Generic;
global using System.Linq;
global using System.Threading.Tasks;
```

## Project Structure

```
Solution/
├── Solution.sln
├── .editorconfig
├── .gitignore
├── Directory.Build.props        # Shared MSBuild properties
├── Directory.Packages.props     # Central Package Management
├── README.md
├── src/
│   ├── CompanyName.ProductName.Domain/
│   │   ├── Models/
│   │   │   └── User.cs
│   │   ├── Interfaces/
│   │   │   └── IUserRepository.cs
│   │   └── CompanyName.ProductName.Domain.csproj
│   ├── CompanyName.ProductName.Application/
│   │   ├── Services/
│   │   │   └── UserService.cs
│   │   └── CompanyName.ProductName.Application.csproj
│   ├── CompanyName.ProductName.Infrastructure/
│   │   ├── Repositories/
│   │   │   └── UserRepository.cs
│   │   └── CompanyName.ProductName.Infrastructure.csproj
│   └── CompanyName.ProductName.Api/
│       ├── Controllers/
│       │   └── UsersController.cs
│       ├── Program.cs
│       ├── appsettings.json
│       └── CompanyName.ProductName.Api.csproj
└── tests/
    ├── CompanyName.ProductName.UnitTests/
    │   ├── Services/
    │   │   └── UserServiceTests.cs
    │   └── CompanyName.ProductName.UnitTests.csproj
    └── CompanyName.ProductName.IntegrationTests/
        └── CompanyName.ProductName.IntegrationTests.csproj
```

## Dependency Injection Pattern (Required)

```csharp
// Program.cs (ASP.NET Core)
var builder = WebApplication.CreateBuilder(args);

// Register services
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("Default")));

var app = builder.Build();
app.Run();

// Controller with DI
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly ILogger<UsersController> _logger;
    
    public UsersController(IUserService userService, ILogger<UsersController> logger)
    {
        _userService = userService;
        _logger = logger;
    }
    
    [HttpGet("{id}")]
    public async Task<ActionResult<User>> GetUser(int id)
    {
        try
        {
            var user = await _userService.GetUserAsync(id);
            return Ok(user);
        }
        catch (NotFoundException ex)
        {
            return NotFound(ex.Message);
        }
    }
}
```

## Error Handling

```csharp
// Custom exception hierarchy
public class ApplicationException : Exception
{
    public ApplicationException(string message) : base(message) { }
    public ApplicationException(string message, Exception inner) : base(message, inner) { }
}

public class ValidationException : ApplicationException
{
    public Dictionary<string, string[]> Errors { get; }
    
    public ValidationException(Dictionary<string, string[]> errors) 
        : base("Validation failed")
    {
        Errors = errors;
    }
}

public class NotFoundException : ApplicationException
{
    public NotFoundException(string resource) 
        : base($"{resource} not found") { }
}

// Proper async exception handling
try
{
    var result = await RiskyOperationAsync();
}
catch (HttpRequestException ex)
{
    _logger.LogError(ex, "API call failed");
    throw new ServiceUnavailableException("External service unavailable", ex);
}
catch (Exception ex)
{
    _logger.LogError(ex, "Unexpected error");
    throw;
}

// Result pattern (alternative to exceptions)
public record Result<T>
{
    public bool IsSuccess { get; init; }
    public T? Value { get; init; }
    public string? Error { get; init; }
    
    public static Result<T> Success(T value) => new() { IsSuccess = true, Value = value };
    public static Result<T> Failure(string error) => new() { IsSuccess = false, Error = error };
}

public async Task<Result<User>> GetUserAsync(int id)
{
    try
    {
        var user = await _repository.FindByIdAsync(id);
        return user is not null 
            ? Result<User>.Success(user)
            : Result<User>.Failure("User not found");
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Failed to get user");
        return Result<User>.Failure(ex.Message);
    }
}
```

## Configuration (.csproj)

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <WarningsAsErrors />
    <NoWarn>$(NoWarn);1591</NoWarn> <!-- Ignore missing XML comments warning -->
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Logging" Version="8.0.0" />
  </ItemGroup>
</Project>
```

## .editorconfig

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.cs]
indent_style = space
indent_size = 4

# Naming conventions
dotnet_naming_rule.interfaces_should_be_prefixed_with_i.severity = warning
dotnet_naming_rule.interfaces_should_be_prefixed_with_i.symbols = interface
dotnet_naming_rule.interfaces_should_be_prefixed_with_i.style = begins_with_i

dotnet_naming_rule.private_fields_should_be_prefixed_with_underscore.severity = warning
dotnet_naming_rule.private_fields_should_be_prefixed_with_underscore.symbols = private_field
dotnet_naming_rule.private_fields_should_be_prefixed_with_underscore.style = begins_with_underscore

# Code style
csharp_prefer_braces = true:warning
csharp_using_directive_placement = outside_namespace:warning
csharp_prefer_var_type = when_type_is_apparent:suggestion
```

## Tools to Use

**Build & Test:**
- `dotnet build` - Build solution
- `dotnet test` - Run tests
- `dotnet run` - Run application

**Code Quality:**
- `dotnet format` - Code formatter (built-in)
- SonarAnalyzer - Advanced static analysis
- Roslynator - Additional analyzers

**Testing:**
- xUnit - Preferred test framework
- NUnit - Alternative
- Moq or NSubstitute - Mocking

**Coverage:**
- coverlet - Code coverage tool

## Quick Commands

```bash
# Build and test
dotnet build
dotnet test
dotnet test --collect:"XPlat Code Coverage"

# Format
dotnet format

# Run with watch (development)
dotnet watch run

# Create new project
dotnet new webapi -n ProjectName
dotnet new classlib -n ProjectName.Domain
dotnet new xunit -n ProjectName.Tests

# Add packages
dotnet add package PackageName
```

## Best Practices

1. **Enable nullable reference types** - Always
2. **Use async/await consistently** - For all I/O operations
3. **Inject dependencies via constructor** - No service locator
4. **Use IDisposable properly** - With using statements
5. **Prefer records for DTOs** - Immutable by default
6. **Use pattern matching** - More readable than if/else chains
7. **XML documentation comments** - For public APIs
8. **Follow Microsoft conventions** - Use official guidelines

## Anti-Patterns to Avoid

❌ **Nullable warnings disabled**
```csharp
#nullable disable  // Never do this!
```

✅ **Nullable enabled**
```csharp
#nullable enable
public User? FindUser(int id) => _repository.Find(id);
```

❌ **Blocking on async**
```csharp
var result = GetUserAsync().Result;  // Causes deadlocks!
```

✅ **Proper async/await**
```csharp
var result = await GetUserAsync();
```

❌ **Service locator pattern**
```csharp
var service = ServiceLocator.Get<IUserService>();
```

✅ **Constructor injection**
```csharp
public class Controller
{
    private readonly IUserService _userService;
    public Controller(IUserService userService) => _userService = userService;
}
```

## Code Quality Standards

- Line length: 120 characters
- Nullable: Enabled
- Warnings as errors: Yes
- Code coverage: >80% overall, >90% for critical paths
- XML documentation: Required for public APIs
