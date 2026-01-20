"""Shared pytest fixtures for C# module testing."""

import pytest
from csharp_semantic_analyzer import CSharpTypeInfo, ArchitecturalRole


@pytest.fixture
def sample_controller_code():
    """Sample C# controller with DI and attributes."""
    return '''
using System;
using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;

namespace MyApp.Controllers {
    [ApiController]
    [Route("api/[controller]")]
    public class UserController {
        private readonly IUserService userService;
        private readonly IMediator mediator;

        public UserController(IUserService service, IMediator med) {
            userService = service;
            mediator = med;
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetUser(int id) {
            var user = await userService.GetUserById(id);
            return Ok(user);
        }

        [HttpPost]
        public async Task<IActionResult> CreateUser([FromBody] CreateUserDto dto) {
            var command = new CreateUserCommand { Name = dto.Name };
            var result = await mediator.Send(command);
            return Created("", result);
        }
    }
}
'''


@pytest.fixture
def sample_service_code():
    """Sample C# service class."""
    return '''
using System.Threading.Tasks;
using MyApp.Models;
using MyApp.Data;

namespace MyApp.Services {
    public interface IUserService {
        Task<User> GetUserById(int id);
        Task<User> CreateUser(string name);
    }

    public class UserService : IUserService {
        private readonly IUserRepository repository;

        public UserService(IUserRepository repo) {
            repository = repo;
        }

        public async Task<User> GetUserById(int id) {
            return await repository.GetById(id);
        }

        public async Task<User> CreateUser(string name) {
            var user = new User { Name = name };
            return await repository.Create(user);
        }
    }
}
'''


@pytest.fixture
def sample_repository_code():
    """Sample C# repository class."""
    return '''
using System.Threading.Tasks;
using MyApp.Models;
using Microsoft.EntityFrameworkCore;

namespace MyApp.Data {
    public interface IUserRepository {
        Task<User> GetById(int id);
        Task<User> Create(User user);
    }

    public class UserRepository : IUserRepository {
        private readonly AppDbContext context;

        public UserRepository(AppDbContext ctx) {
            context = ctx;
        }

        public async Task<User> GetById(int id) {
            return await context.Users.FindAsync(id);
        }

        public async Task<User> Create(User user) {
            context.Users.Add(user);
            await context.SaveChangesAsync();
            return user;
        }
    }
}
'''


@pytest.fixture
def sample_cohesive_class():
    """Sample cohesive class (high LCOM)."""
    return '''
public class User {
    private string name;
    private string email;
    private int age;

    public void SetName(string n) { name = n; }
    public void SetEmail(string e) { email = e; }
    public void SetAge(int a) { age = a; }

    public string GetName() { return name; }
    public string GetEmail() { return email; }
    public int GetAge() { return age; }
}
'''


@pytest.fixture
def sample_god_object():
    """Sample God Object with low cohesion (LCOM > 0.8)."""
    return '''
public class UserService {
    // User management
    public void CreateUser(string name) { }
    public void DeleteUser(int id) { }
    public void UpdateUser(int id, string name) { }

    // Order processing
    public void CreateOrder(int userId) { }
    public void CancelOrder(int orderId) { }
    public decimal CalculateOrderTotal(int orderId) { }

    // Email notifications
    public void SendWelcomeEmail(string email) { }
    public void SendOrderConfirmation(int orderId) { }
    public void SendNotification(string message) { }

    // Reporting
    public void GenerateUserReport() { }
    public void GenerateOrderReport() { }
    public void ExportData(string format) { }

    // Logging
    private void Log(string message) { }
    private void LogError(string error) { }
    private void LogWarning(string warning) { }
}
'''


@pytest.fixture
def sample_async_issue():
    """Sample code with async-over-sync anti-pattern."""
    return '''
public class UserService {
    private readonly IMediator mediator;

    public UserService(IMediator m) {
        mediator = m;
    }

    // Bad: Using .Result on async method
    public User GetUser(int id) {
        var query = new GetUserQuery { Id = id };
        var result = mediator.Send(query).Result;  // ❌ BLOCKING!
        return result;
    }

    // Bad: Using .Wait()
    public void ProcessUsers(List<int> ids) {
        var tasks = ids.Select(id => ProcessUserAsync(id)).ToList();
        Task.WaitAll(tasks.ToArray());  // ❌ BLOCKING!
    }

    private async Task ProcessUserAsync(int id) {
        await Task.Delay(100);
    }
}
'''


@pytest.fixture
def sample_di_program_cs():
    """Sample Program.cs with DI registrations."""
    return '''
using Microsoft.Extensions.DependencyInjection;
using MyApp.Services;
using MyApp.Data;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<AppDbContext>();
builder.Services.AddMediatR(typeof(Program));

var app = builder.Build();
app.MapControllers();
app.Run();
'''


@pytest.fixture
def sample_cyclic_dependency_code():
    """Code samples for cyclic dependency detection."""
    return {
        "A": "public class A { private B b; }",
        "B": "public class B { private C c; }",
        "C": "public class C { private A a; }"  # Creates cycle: A → B → C → A
    }


@pytest.fixture
def sample_sql_access_code():
    """Sample code with direct SQL access in wrong layer."""
    return '''
using Microsoft.Data.SqlClient;

namespace MyApp.Controllers {
    [ApiController]
    public class UserController {
        [HttpGet("{id}")]
        public IActionResult GetUser(int id) {
            // ❌ BAD: Direct SQL in controller
            using (var conn = new SqlConnection("...")) {
                using (var cmd = new SqlCommand("SELECT * FROM Users WHERE Id = @id", conn)) {
                    cmd.Parameters.AddWithValue("@id", id);
                    // ... execute ...
                }
            }
            return Ok();
        }
    }
}
'''


@pytest.fixture
def sample_partial_class():
    """Sample partial class (should be aggregated)."""
    return [
        '''
namespace MyApp.Models {
    public partial class User {
        public int Id { get; set; }
        public string Name { get; set; }
    }
}
''',
        '''
namespace MyApp.Models {
    public partial class User {
        public string Email { get; set; }
        public DateTime CreatedAt { get; set; }
    }
}
'''
    ]


@pytest.fixture
def sample_mediatr_handler():
    """Sample MediatR handler (should depend only on Domain)."""
    return '''
using MediatR;
using MyApp.Domain;

namespace MyApp.Handlers {
    public class CreateUserHandler : IRequestHandler<CreateUserCommand, User> {
        private readonly IUserRepository repository;

        public CreateUserHandler(IUserRepository repo) {
            repository = repo;
        }

        public async Task<User> Handle(CreateUserCommand request, CancellationToken cancellationToken) {
            var user = new User { Name = request.Name };
            return await repository.Create(user);
        }
    }
}
'''


@pytest.fixture
def sample_singleton_code():
    """Sample code with Singleton pattern."""
    return '''
public class DatabaseConnection {
    private static readonly DatabaseConnection instance = new();

    private DatabaseConnection() { }

    public static DatabaseConnection Instance => instance;

    public void Connect() { }
}
'''


@pytest.fixture
def sample_factory_code():
    """Sample code with Factory pattern."""
    return '''
public class DataAccessFactory {
    public static IDataAccess Create(string type) {
        return type switch {
            "sql" => new SqlDataAccess(),
            "mongo" => new MongoDataAccess(),
            _ => throw new ArgumentException()
        };
    }
}
'''


@pytest.fixture
def sample_builder_code():
    """Sample code with Builder pattern."""
    return '''
public class QueryBuilder {
    private string _from;
    private string _where;

    public QueryBuilder From(string table) {
        _from = table;
        return this;
    }

    public QueryBuilder Where(string condition) {
        _where = condition;
        return this;
    }

    public string Build() {
        return $"SELECT * FROM {_from} WHERE {_where}";
    }
}
'''


@pytest.fixture
def detector():
    """Create CSharpPatternDetector instance."""
    from csharp_pattern_detector import CSharpPatternDetector
    return CSharpPatternDetector()
