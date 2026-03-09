# C# Testing Guide

---
**Language:** C#
**Test Framework:** xUnit (recommended), NUnit, MSTest
**Coverage Tool:** coverlet, dotCover
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
```csharp
// Tests/UserServiceTests.cs
using Xunit;

public class UserServiceTests
{
    [Fact]
    public async Task RegisterUser_WithValidData_ReturnsSuccess()
    {
        // Arrange
        var service = new UserService();
        var email = "test@example.com";
        var password = "SecurePass123!";
        
        // Act
        var result = await service.RegisterAsync(email, password);
        
        // Assert
        Assert.True(result.Success);
        Assert.Equal(email, result.User.Email);
        Assert.NotEqual(password, result.User.Password); // Should be hashed
        Assert.NotEmpty(result.User.Id);
    }
}

// Run: dotnet test
// Expected: FAIL - UserService.RegisterAsync doesn't exist
```

**Step 2: Minimal implementation (GREEN)**
```csharp
// Services/UserService.cs
public record RegistrationResult(bool Success, User User);

public class UserService
{
    public async Task<RegistrationResult> RegisterAsync(string email, string password)
    {
        var hashedPassword = BCrypt.Net.BCrypt.HashPassword(password);
        var user = new User
        {
            Id = Guid.NewGuid().ToString(),
            Email = email,
            Password = hashedPassword
        };
        
        return new RegistrationResult(true, user);
    }
}

// Run: dotnet test
// Expected: PASS
```

**Step 3: Refactor (REFACTOR)**
```csharp
// Extract password hashing
public interface IPasswordHasher
{
    string Hash(string password);
}

public class PasswordHasher : IPasswordHasher
{
    public string Hash(string password) => BCrypt.Net.BCrypt.HashPassword(password);
}

public class UserService
{
    private readonly IPasswordHasher _hasher;
    
    public UserService(IPasswordHasher hasher)
    {
        _hasher = hasher;
    }
    
    public async Task<RegistrationResult> RegisterAsync(string email, string password)
    {
        var hashedPassword = _hasher.Hash(password);
        var user = new User
        {
            Id = Guid.NewGuid().ToString(),
            Email = email,
            Password = hashedPassword
        };
        
        return new RegistrationResult(true, user);
    }
}

// Run: dotnet test
// Expected: Still PASS (update test to inject hasher)
```

## Project Structure

```
Solution/
├── src/
│   ├── MyApp/
│   │   ├── MyApp.csproj
│   │   ├── Models/
│   │   │   └── User.cs
│   │   ├── Services/
│   │   │   └── UserService.cs
│   │   └── Repositories/
│   │       └── UserRepository.cs
└── tests/
    ├── MyApp.Tests/
    │   ├── MyApp.Tests.csproj
    │   ├── Unit/
    │   │   └── UserServiceTests.cs
    │   └── Integration/
    │       └── UserRepositoryTests.cs
    └── MyApp.IntegrationTests/
        └── ApiTests.cs
```

## xUnit Configuration (.csproj)

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="xunit" Version="2.6.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.4" />
    <PackageReference Include="Moq" Version="4.20.69" />
    <PackageReference Include="FluentAssertions" Version="6.12.0" />
    <PackageReference Include="coverlet.collector" Version="6.0.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\..\src\MyApp\MyApp.csproj" />
  </ItemGroup>
</Project>
```

## Unit Tests (70% of tests)

### Basic xUnit Test Structure

```csharp
using Xunit;

public class CalculatorTests
{
    private readonly Calculator _calculator;
    
    public CalculatorTests()
    {
        // Constructor runs before each test
        _calculator = new Calculator();
    }
    
    [Fact]
    public void Add_TwoPositiveNumbers_ReturnsSum()
    {
        // Arrange
        var a = 2;
        var b = 3;
        
        // Act
        var result = _calculator.Add(a, b);
        
        // Assert
        Assert.Equal(5, result);
    }
    
    [Fact]
    public void Divide_ByZero_ThrowsException()
    {
        Assert.Throws<DivideByZeroException>(() => _calculator.Divide(10, 0));
    }
}
```

### Theory Tests (Parametrized)

```csharp
public class AgeValidatorTests
{
    [Theory]
    [InlineData(17, false)]  // Below minimum
    [InlineData(18, true)]   // Minimum
    [InlineData(19, true)]   // Above minimum
    [InlineData(119, true)]  // Below maximum
    [InlineData(120, true)]  // Maximum
    [InlineData(121, false)] // Above maximum
    public void IsValid_WithVariousAges_ReturnsExpected(int age, bool expected)
    {
        var validator = new AgeValidator(minAge: 18, maxAge: 120);
        
        var result = validator.IsValid(age);
        
        Assert.Equal(expected, result);
    }
    
    [Theory]
    [InlineData("test@example.com", true)]
    [InlineData("invalid.email", false)]
    [InlineData("@example.com", false)]
    [InlineData("test@", false)]
    [InlineData(null, false)]
    [InlineData("", false)]
    public void ValidateEmail_WithVariousInputs_ReturnsExpected(
        string? email, 
        bool expectedValid)
    {
        var validator = new EmailValidator();
        
        var result = validator.Validate(email);
        
        Assert.Equal(expectedValid, result.IsValid);
    }
}
```

### Class Fixtures (Shared Setup)

```csharp
// Fixture class
public class DatabaseFixture : IDisposable
{
    public AppDbContext Context { get; }
    
    public DatabaseFixture()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        
        Context = new AppDbContext(options);
        Context.Database.EnsureCreated();
    }
    
    public void Dispose()
    {
        Context.Database.EnsureDeleted();
        Context.Dispose();
    }
}

// Test class using fixture
public class UserRepositoryTests : IClassFixture<DatabaseFixture>
{
    private readonly DatabaseFixture _fixture;
    
    public UserRepositoryTests(DatabaseFixture fixture)
    {
        _fixture = fixture;
    }
    
    [Fact]
    public async Task Save_WithValidUser_PersistsToDatabase()
    {
        // Use _fixture.Context
        var repository = new UserRepository(_fixture.Context);
        var user = new User { Email = "test@example.com", Name = "Test" };
        
        await repository.SaveAsync(user);
        var retrieved = await repository.FindByEmailAsync("test@example.com");
        
        Assert.NotNull(retrieved);
        Assert.Equal(user.Email, retrieved.Email);
    }
}
```

## Mocking with Moq

```csharp
using Moq;

public class UserServiceTests
{
    [Fact]
    public async Task GetUser_CallsRepository()
    {
        // Arrange
        var mockRepo = new Mock<IUserRepository>();
        mockRepo.Setup(repo => repo.FindByIdAsync(1))
                .ReturnsAsync(new User { Id = 1, Name = "Alice" });
        
        var service = new UserService(mockRepo.Object);
        
        // Act
        var result = await service.GetUserAsync(1);
        
        // Assert
        Assert.Equal("Alice", result.Name);
        mockRepo.Verify(repo => repo.FindByIdAsync(1), Times.Once);
    }
    
    [Fact]
    public async Task CreateUser_WithException_HandlesGracefully()
    {
        // Arrange
        var mockRepo = new Mock<IUserRepository>();
        mockRepo.Setup(repo => repo.SaveAsync(It.IsAny<User>()))
                .ThrowsAsync(new DatabaseException("Connection failed"));
        
        var service = new UserService(mockRepo.Object);
        
        // Act & Assert
        await Assert.ThrowsAsync<ServiceException>(
            () => service.CreateUserAsync("test@example.com", "Test")
        );
    }
    
    [Fact]
    public void SendEmail_CallsEmailService_WithCorrectParameters()
    {
        // Arrange
        var mockEmailService = new Mock<IEmailService>();
        var notifier = new UserNotifier(mockEmailService.Object);
        
        // Act
        notifier.NotifyUser("test@example.com", "Welcome!");
        
        // Assert
        mockEmailService.Verify(
            svc => svc.Send(
                "test@example.com",
                It.Is<string>(s => s.Contains("Welcome!"))),
            Times.Once
        );
    }
}
```

## FluentAssertions (Better Assertions)

```csharp
using FluentAssertions;

public class UserServiceTests
{
    [Fact]
    public async Task GetUser_WithValidId_ReturnsUser()
    {
        var service = new UserService();
        
        var result = await service.GetUserAsync(1);
        
        // More readable assertions
        result.Should().NotBeNull();
        result.Id.Should().Be(1);
        result.Email.Should().Be("test@example.com");
        result.CreatedAt.Should().BeCloseTo(DateTime.UtcNow, TimeSpan.FromSeconds(5));
    }
    
    [Fact]
    public void GetUsers_ReturnsMultipleUsers()
    {
        var service = new UserService();
        
        var users = service.GetUsers();
        
        users.Should().HaveCount(3);
        users.Should().Contain(u => u.Email == "admin@example.com");
        users.Should().OnlyContain(u => u.IsActive);
        users.Should().BeInAscendingOrder(u => u.Name);
    }
    
    [Fact]
    public void Validate_WithInvalidEmail_ReturnsErrors()
    {
        var validator = new UserValidator();
        var user = new User { Email = "invalid" };
        
        var result = validator.Validate(user);
        
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.PropertyName == "Email");
    }
}
```

## Integration Tests (20% of tests)

```csharp
public class UserRepositoryIntegrationTests : IDisposable
{
    private readonly AppDbContext _context;
    private readonly UserRepository _repository;
    
    public UserRepositoryIntegrationTests()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        
        _context = new AppDbContext(options);
        _repository = new UserRepository(_context);
        
        // Seed test data
        _context.Users.AddRange(
            new User { Id = 1, Email = "alice@example.com", Name = "Alice" },
            new User { Id = 2, Email = "bob@example.com", Name = "Bob" }
        );
        _context.SaveChanges();
    }
    
    [Fact]
    public async Task SaveAsync_PersistsUser()
    {
        var user = new User { Email = "new@example.com", Name = "New User" };
        
        await _repository.SaveAsync(user);
        var retrieved = await _repository.FindByEmailAsync("new@example.com");
        
        retrieved.Should().NotBeNull();
        retrieved!.Email.Should().Be(user.Email);
    }
    
    [Fact]
    public async Task DeleteAsync_RemovesUser()
    {
        await _repository.DeleteAsync(1);
        
        var user = await _repository.FindByIdAsync(1);
        user.Should().BeNull();
    }
    
    public void Dispose()
    {
        _context.Database.EnsureDeleted();
        _context.Dispose();
    }
}
```

## Async Testing

```csharp
public class AsyncServiceTests
{
    [Fact]
    public async Task FetchDataAsync_ReturnsData()
    {
        var service = new DataService();
        
        var result = await service.FetchDataAsync();
        
        result.Should().NotBeNull();
        result.Count.Should().BeGreaterThan(0);
    }
    
    [Fact]
    public async Task ProcessAsync_WithCancellation_ThrowsOperationCanceledException()
    {
        var service = new DataService();
        var cts = new CancellationTokenSource();
        cts.Cancel();
        
        await Assert.ThrowsAsync<OperationCanceledException>(
            () => service.ProcessAsync(cts.Token)
        );
    }
    
    [Fact]
    public async Task RetryAsync_AfterFailures_Succeeds()
    {
        var mockService = new Mock<IExternalService>();
        mockService.SetupSequence(s => s.CallAsync())
            .ThrowsAsync(new HttpRequestException())
            .ThrowsAsync(new HttpRequestException())
            .ReturnsAsync("Success");
        
        var retryService = new RetryService(mockService.Object);
        
        var result = await retryService.CallWithRetryAsync();
        
        result.Should().Be("Success");
        mockService.Verify(s => s.CallAsync(), Times.Exactly(3));
    }
}
```

## Edge Cases and Error Testing

```csharp
public class ValidationTests
{
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ValidateEmail_WithInvalidInput_ReturnsFalse(string? email)
    {
        var validator = new EmailValidator();
        
        var result = validator.Validate(email);
        
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain("Email is required");
    }
    
    [Fact]
    public void ProcessFile_WhenFileNotFound_ThrowsFileNotFoundException()
    {
        var service = new FileService();
        
        Action act = () => service.ProcessFile("nonexistent.txt");
        
        act.Should().Throw<FileNotFoundException>()
            .WithMessage("*nonexistent.txt*");
    }
    
    [Fact]
    public void Divide_WithMaxValues_HandlesOverflow()
    {
        var calculator = new Calculator();
        
        var result = calculator.Divide(int.MaxValue, 0.5);
        
        result.Should().BeApproximately(2147483647 * 2, 1);
    }
}
```

## Test Data Builders

```csharp
public class UserBuilder
{
    private string _email = "test@example.com";
    private string _name = "Test User";
    private string _role = "User";
    private bool _isActive = true;
    
    public UserBuilder WithEmail(string email)
    {
        _email = email;
        return this;
    }
    
    public UserBuilder WithName(string name)
    {
        _name = name;
        return this;
    }
    
    public UserBuilder WithRole(string role)
    {
        _role = role;
        return this;
    }
    
    public UserBuilder Inactive()
    {
        _isActive = false;
        return this;
    }
    
    public User Build() => new User
    {
        Id = Guid.NewGuid().ToString(),
        Email = _email,
        Name = _name,
        Role = _role,
        IsActive = _isActive
    };
}

// Usage
[Fact]
public void AdminUser_CanDeleteUsers()
{
    var admin = new UserBuilder()
        .WithRole("Admin")
        .Build();
    
    admin.CanDeleteUsers().Should().BeTrue();
}
```

## Coverage Commands

```bash
# Run tests
dotnet test

# Run with coverage
dotnet test /p:CollectCoverage=true

# Generate HTML coverage report
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura
reportgenerator -reports:coverage.cobertura.xml -targetdir:coveragereport

# Run specific test
dotnet test --filter "FullyQualifiedName=MyApp.Tests.UserServiceTests.GetUser_ReturnsUser"

# Run tests in category
dotnet test --filter "Category=Integration"

# Verbose output
dotnet test --logger "console;verbosity=detailed"
```

## Test Categories

```csharp
public class UserServiceTests
{
    [Fact]
    [Trait("Category", "Unit")]
    public void GetUser_WithValidId_ReturnsUser()
    {
        // Unit test
    }
    
    [Fact]
    [Trait("Category", "Integration")]
    public async Task SaveUser_PersistsToDatabase()
    {
        // Integration test
    }
    
    [Fact]
    [Trait("Category", "Slow")]
    public async Task ProcessLargeDataset_Succeeds()
    {
        // Slow test
    }
}

// Run specific category
// dotnet test --filter "Category=Unit"
// dotnet test --filter "Category!=Slow"
```

## Best Practices

1. **Use xUnit** for new projects (best async support)
2. **Use FluentAssertions** for readable assertions
3. **Mock external dependencies** with Moq
4. **Use Theory for parametrized tests**
5. **Follow AAA pattern** (Arrange, Act, Assert)
6. **Use async/await** properly in tests
7. **Use InMemoryDatabase** for EF Core integration tests
8. **Dispose resources** properly (IDisposable)
9. **Aim for 80%+ coverage** on business logic
10. **Use builders** for complex test data

## Anti-Patterns to Avoid

❌ **Testing private methods**
```csharp
// Don't use reflection to test private methods
var method = typeof(UserService).GetMethod("InternalHelper", BindingFlags.NonPublic);
```

✅ **Test public behavior**
```csharp
[Fact]
public void PublicMethod_ProducesCorrectResult()
{
    var result = service.PublicMethod();
    result.Should().Be(expected);
}
```

❌ **Test interdependence**
```csharp
private static User? _testUser;

[Fact]
public void Test1_CreatesUser()
{
    _testUser = new User();  // State leak!
}

[Fact]
public void Test2_UsesUser()
{
    Assert.NotNull(_testUser);  // Depends on Test1
}
```

✅ **Independent tests with fixtures**
```csharp
[Fact]
public void Test1_CreatesUser()
{
    var user = CreateTestUser();  // Independent
}

[Fact]
public void Test2_UsesUser()
{
    var user = CreateTestUser();  // Independent
}
```

## Quick Reference

```bash
# Run all tests
dotnet test

# Run with verbosity
dotnet test -v detailed

# Run specific test
dotnet test --filter FullyQualifiedName~UserServiceTests

# Run with coverage
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# Watch mode
dotnet watch test

# Parallel execution (default in xUnit)
dotnet test --parallel
```
