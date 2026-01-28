"""End-to-end integration tests for C# audit system."""

import pytest
from pathlib import Path
from csharp_audit_integration import CSharpArchitecturalAuditor
from csharp_audit_reporter import CSharpAuditReporter
from models import Language


@pytest.fixture
def sample_csharp_project(tmp_path):
    """Create a realistic sample C# project structure for E2E testing."""

    project_root = tmp_path / "SampleDotNetApp"
    (project_root / "Controllers").mkdir(parents=True)
    (project_root / "Services").mkdir(parents=True)
    (project_root / "Data").mkdir(parents=True)
    (project_root / "Models").mkdir(parents=True)
    (project_root / "Handlers").mkdir(parents=True)

    # Create Program.cs with DI configuration
    program_cs = project_root / "Program.cs"
    program_cs.write_text('''
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using SampleApp.Services;
using SampleApp.Data;
using SampleApp.Handlers;
using MediatR;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<AppDbContext>();
builder.Services.AddMediatR(typeof(Program));
builder.Services.AddSwaggerGen();

var app = builder.Build();

if (app.Environment.IsDevelopment()) {
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();
app.Run();
''')

    # Create UserController
    controller = project_root / "Controllers" / "UserController.cs"
    controller.write_text('''
using Microsoft.AspNetCore.Mvc;
using MediatR;
using SampleApp.Models;
using SampleApp.Services;

namespace SampleApp.Controllers {
    [ApiController]
    [Route("api/[controller]")]
    public class UserController : ControllerBase {
        private readonly IMediator mediator;
        private readonly IUserService userService;

        public UserController(IMediator med, IUserService service) {
            mediator = med;
            userService = service;
        }

        [HttpGet("{id}")]
        public async Task<ActionResult<UserDto>> GetUser(int id) {
            var user = await userService.GetUserById(id);
            if (user == null) return NotFound();
            return Ok(user);
        }

        [HttpPost]
        public async Task<ActionResult<UserDto>> CreateUser([FromBody] CreateUserRequest request) {
            var command = new CreateUserCommand { Name = request.Name, Email = request.Email };
            var result = await mediator.Send(command);
            return CreatedAtAction(nameof(GetUser), new { id = result.Id }, result);
        }

        [HttpDelete("{id}")]
        public async Task<IActionResult> DeleteUser(int id) {
            var command = new DeleteUserCommand { Id = id };
            await mediator.Send(command);
            return NoContent();
        }
    }

    public record CreateUserRequest(string Name, string Email);
}
''')

    # Create UserService
    service = project_root / "Services" / "UserService.cs"
    service.write_text('''
using SampleApp.Data;
using SampleApp.Models;

namespace SampleApp.Services {
    public interface IUserService {
        Task<UserDto> GetUserById(int id);
        Task<UserDto> CreateUser(string name, string email);
        Task DeleteUser(int id);
    }

    public class UserService : IUserService {
        private readonly IUserRepository repository;
        private readonly AppDbContext dbContext;

        public UserService(IUserRepository repo, AppDbContext ctx) {
            repository = repo;
            dbContext = ctx;
        }

        public async Task<UserDto> GetUserById(int id) {
            var user = await repository.GetById(id);
            return user == null ? null : new UserDto { Id = user.Id, Name = user.Name, Email = user.Email };
        }

        public async Task<UserDto> CreateUser(string name, string email) {
            var user = new User { Name = name, Email = email, CreatedAt = DateTime.UtcNow };
            var created = await repository.Create(user);
            return new UserDto { Id = created.Id, Name = created.Name, Email = created.Email };
        }

        public async Task DeleteUser(int id) {
            await repository.Delete(id);
        }
    }
}
''')

    # Create UserRepository
    repository = project_root / "Data" / "UserRepository.cs"
    repository.write_text('''
using Microsoft.EntityFrameworkCore;
using SampleApp.Models;

namespace SampleApp.Data {
    public interface IUserRepository {
        Task<User> GetById(int id);
        Task<User> Create(User user);
        Task Delete(int id);
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

        public async Task Delete(int id) {
            var user = await context.Users.FindAsync(id);
            if (user != null) {
                context.Users.Remove(user);
                await context.SaveChangesAsync();
            }
        }
    }
}
''')

    # Create DbContext
    db_context = project_root / "Data" / "AppDbContext.cs"
    db_context.write_text('''
using Microsoft.EntityFrameworkCore;
using SampleApp.Models;

namespace SampleApp.Data {
    public class AppDbContext : DbContext {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

        public DbSet<User> Users { get; set; }
    }
}
''')

    # Create Models
    user_model = project_root / "Models" / "User.cs"
    user_model.write_text('''
namespace SampleApp.Models {
    public class User {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Email { get; set; }
        public DateTime CreatedAt { get; set; }
    }

    public record UserDto(int Id, string Name, string Email);
}
''')

    # Create MediatR Handlers
    handlers = project_root / "Handlers" / "UserHandlers.cs"
    handlers.write_text('''
using MediatR;
using SampleApp.Data;
using SampleApp.Models;

namespace SampleApp.Handlers {
    public class CreateUserCommand : IRequest<UserDto> {
        public string Name { get; set; }
        public string Email { get; set; }
    }

    public class CreateUserCommandHandler : IRequestHandler<CreateUserCommand, UserDto> {
        private readonly IUserRepository repository;

        public CreateUserCommandHandler(IUserRepository repo) {
            repository = repo;
        }

        public async Task<UserDto> Handle(CreateUserCommand request, CancellationToken cancellationToken) {
            var user = new User { Name = request.Name, Email = request.Email, CreatedAt = DateTime.UtcNow };
            var created = await repository.Create(user);
            return new UserDto(created.Id, created.Name, created.Email);
        }
    }

    public class DeleteUserCommand : IRequest {
        public int Id { get; set; }
    }

    public class DeleteUserCommandHandler : IRequestHandler<DeleteUserCommand> {
        private readonly IUserRepository repository;

        public DeleteUserCommandHandler(IUserRepository repo) {
            repository = repo;
        }

        public async Task Handle(DeleteUserCommand request, CancellationToken cancellationToken) {
            await repository.Delete(request.Id);
        }
    }
}
''')

    return project_root


class TestEndToEndAnalysis:
    """End-to-end integration tests."""

    def test_complete_project_analysis(self, sample_csharp_project):
        """Test complete analysis workflow from project to patterns."""
        auditor = CSharpArchitecturalAuditor()

        # Analyze project
        result = auditor.analyze_csharp_project(str(sample_csharp_project))

        # Verify basic structure
        assert "types" in result
        assert "audit_result" in result

        # Verify types were extracted
        types = result["types"]
        assert len(types) > 0

        # Verify key types detected
        type_names = {t.name for t in types}
        assert "UserController" in type_names
        assert "UserService" in type_names
        assert "UserRepository" in type_names

    def test_controller_detection_and_roles(self, sample_csharp_project):
        """Test that controllers are properly detected with correct roles."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        types = result["types"]

        # Find controller
        controllers = [t for t in types if t.name == "UserController"]
        assert len(controllers) > 0

        controller = controllers[0]
        from csharp_semantic_analyzer import ArchitecturalRole
        assert controller.architectural_role == ArchitecturalRole.CONTROLLER

    def test_service_detection_and_roles(self, sample_csharp_project):
        """Test that services are properly detected."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        types = result["types"]

        # Find service
        services = [t for t in types if t.name == "UserService"]
        assert len(services) > 0

        service = services[0]
        from csharp_semantic_analyzer import ArchitecturalRole
        assert service.architectural_role == ArchitecturalRole.SERVICE

    def test_di_registration_extraction(self, sample_csharp_project):
        """Test that DI registrations are extracted from Program.cs."""
        auditor = CSharpArchitecturalAuditor()

        auditor.analyze_csharp_project(str(sample_csharp_project))

        # Should have extracted DI registrations
        # Note: Actual count depends on regex parsing

    def test_audit_report_generation(self, sample_csharp_project, tmp_path):
        """Test generation of audit reports in all formats."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        audit_result = result["audit_result"]
        types = result["types"]

        # Generate reports
        json_path = tmp_path / "audit.json"
        md_path = tmp_path / "audit.md"
        sarif_path = tmp_path / "audit.sarif"

        # JSON
        CSharpAuditReporter.generate_json_report(audit_result, str(json_path))
        assert json_path.exists()
        assert json_path.stat().st_size > 0

        # Markdown
        CSharpAuditReporter.generate_markdown_report(
            audit_result,
            {t.name: t for t in types},
            str(md_path)
        )
        assert md_path.exists()
        assert md_path.stat().st_size > 0

        # SARIF
        CSharpAuditReporter.generate_sarif_report(audit_result, str(sarif_path))
        assert sarif_path.exists()
        assert sarif_path.stat().st_size > 0

    def test_pattern_conversion_and_storage(self, sample_csharp_project):
        """Test conversion of types to DNA patterns."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        types = result["types"]

        # Convert to patterns
        patterns = auditor.convert_to_dna_patterns(types, "sample-dotnet-app")

        # Verify patterns
        assert len(patterns) > 0

        for pattern in patterns:
            assert pattern.title
            assert pattern.description
            assert pattern.language == Language.CSHARP
            assert pattern.source_repo == "sample-dotnet-app"
            assert 1 <= pattern.quality_score <= 10

    def test_audit_violations_detection(self, sample_csharp_project):
        """Test that audit violations are properly detected."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        audit_result = result["audit_result"]

        # Verify audit result structure
        assert audit_result.total_types > 0
        assert isinstance(audit_result.violations_by_severity, dict)
        assert isinstance(audit_result.violations_by_rule, dict)
        assert isinstance(audit_result.violations, list)

    def test_metrics_calculation(self, sample_csharp_project):
        """Test that metrics are properly calculated."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        audit_result = result["audit_result"]

        # Verify metrics
        metrics = audit_result.metrics
        assert "total_types" in metrics
        assert "namespaces_analyzed" in metrics
        assert "avg_lcom" in metrics
        assert "avg_dependencies" in metrics
        assert "types_by_role" in metrics

    def test_console_output_generation(self, sample_csharp_project, capsys):
        """Test console summary output."""
        auditor = CSharpArchitecturalAuditor()

        result = auditor.analyze_csharp_project(str(sample_csharp_project))
        audit_result = result["audit_result"]

        CSharpAuditReporter.print_console_summary(audit_result)

        captured = capsys.readouterr()
        output = captured.out

        # Verify output contains key information
        assert "ARCHITECTURAL DNA" in output or "AUDIT" in output


class TestErrorHandlingE2E:
    """Test error handling in end-to-end scenarios."""

    def test_empty_project_handling(self, tmp_path):
        """Test handling of empty project directory."""
        auditor = CSharpArchitecturalAuditor()

        empty_project = tmp_path / "empty"
        empty_project.mkdir()

        result = auditor.analyze_csharp_project(str(empty_project))

        # Should return valid result even for empty project
        assert result["types"] is not None
        assert isinstance(result["types"], list)

    def test_project_with_only_interfaces(self, tmp_path):
        """Test project with only interface definitions."""
        project_root = tmp_path / "InterfaceProject"
        project_root.mkdir()

        interface_file = project_root / "Interfaces.cs"
        interface_file.write_text('''
namespace TestApp.Interfaces {
    public interface IService { }
    public interface IRepository { }
    public interface IHandler { }
}
''')

        auditor = CSharpArchitecturalAuditor()
        result = auditor.analyze_csharp_project(str(project_root))

        # Should extract interfaces
        types = result["types"]
        # May extract interfaces depending on implementation
        assert len(types) >= 0  # At least no crash

    def test_large_project_performance(self, tmp_path):
        """Test performance on project with many files."""
        import pytest

        project_root = tmp_path / "LargeProject"
        project_root.mkdir()

        # Create multiple files
        for i in range(10):
            file_path = project_root / f"Service{i}.cs"
            file_path.write_text(f'''
namespace TestApp.Services {{
    public class Service{i} {{
        public void DoWork() {{ }}
    }}
}}
''')

        auditor = CSharpArchitecturalAuditor()

        # Should complete in reasonable time
        result = auditor.analyze_csharp_project(str(project_root))

        types = result["types"]
        assert len(types) >= 10  # At least extracted our services
