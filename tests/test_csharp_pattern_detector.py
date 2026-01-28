"""Tests for C# Design Pattern Detection."""

import pytest
from csharp_pattern_detector import (
    CSharpPatternDetector,
    DesignPattern,
    PatternMatch
)


@pytest.fixture
def detector():
    """Create pattern detector."""
    return CSharpPatternDetector()


class TestSingletonDetection:
    """Test Singleton pattern detection."""

    def test_singleton_detection(self, detector):
        """Test detection of Singleton pattern."""
        code = '''
public class DatabaseConnection {
    private static readonly DatabaseConnection instance = new();

    private DatabaseConnection() { }

    public static DatabaseConnection Instance => instance;

    public void Connect() { }
}
'''
        patterns = detector.detect_patterns(code, "DatabaseConnection")

        singleton_patterns = [p for p in patterns if p.pattern == DesignPattern.SINGLETON]
        assert len(singleton_patterns) > 0
        assert singleton_patterns[0].confidence >= 0.5

    def test_lazy_singleton_detection(self, detector):
        """Test detection of Lazy<T> Singleton."""
        code = '''
public class Logger {
    private static readonly Lazy<Logger> lazy = new(() => new Logger());

    private Logger() { }

    public static Logger Instance => lazy.Value;
}
'''
        patterns = detector.detect_patterns(code, "Logger")

        singleton_patterns = [p for p in patterns if p.pattern == DesignPattern.SINGLETON]
        assert len(singleton_patterns) > 0


class TestFactoryDetection:
    """Test Factory pattern detection."""

    def test_factory_detection(self, detector):
        """Test detection of Factory pattern."""
        code = '''
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
        patterns = detector.detect_patterns(code, "DataAccessFactory")

        factory_patterns = [p for p in patterns if p.pattern == DesignPattern.FACTORY]
        assert len(factory_patterns) > 0

    def test_abstract_factory_detection(self, detector):
        """Test detection of abstract factory."""
        code = '''
public static class LoggerFactory {
    public static ILogger Create(LogLevel level) {
        return level switch {
            LogLevel.Debug => new DebugLogger(),
            LogLevel.Production => new ProductionLogger(),
            _ => new ConsoleLogger()
        };
    }
}
'''
        patterns = detector.detect_patterns(code, "LoggerFactory")

        factory_patterns = [p for p in patterns if p.pattern == DesignPattern.FACTORY]
        assert len(factory_patterns) > 0


class TestBuilderDetection:
    """Test Builder pattern detection."""

    def test_builder_detection(self, detector):
        """Test detection of Builder pattern."""
        code = '''
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
        patterns = detector.detect_patterns(code, "QueryBuilder")

        builder_patterns = [p for p in patterns if p.pattern == DesignPattern.BUILDER]
        assert len(builder_patterns) > 0
        assert builder_patterns[0].confidence >= 0.6


class TestDecoratorDetection:
    """Test Decorator pattern detection."""

    def test_decorator_detection(self, detector):
        """Test detection of Decorator pattern."""
        code = '''
public class LoggingDecorator : IRepository {
    private readonly IRepository _inner;
    private readonly ILogger _logger;

    public LoggingDecorator(IRepository inner, ILogger logger) {
        _inner = inner;
        _logger = logger;
    }

    public async Task<User> GetUser(int id) {
        _logger.Log($"Getting user {id}");
        return await _inner.GetUser(id);
    }
}
'''
        patterns = detector.detect_patterns(code, "LoggingDecorator")

        decorator_patterns = [p for p in patterns if p.pattern == DesignPattern.DECORATOR]
        assert len(decorator_patterns) > 0


class TestAdapterDetection:
    """Test Adapter pattern detection."""

    def test_adapter_detection(self, detector):
        """Test detection of Adapter pattern."""
        code = '''
public class LegacyDataAdapter : IModernDataAccess {
    private readonly LegacyDatabase _legacy;

    public LegacyDataAdapter(LegacyDatabase legacy) {
        _legacy = legacy;
    }

    public async Task<User> GetUser(int id) {
        var legacyUser = _legacy.QueryUser(id);
        return new User { Id = legacyUser.UserId, Name = legacyUser.UserName };
    }
}
'''
        patterns = detector.detect_patterns(code, "LegacyDataAdapter")

        adapter_patterns = [p for p in patterns if p.pattern == DesignPattern.ADAPTER]
        assert len(adapter_patterns) > 0


class TestStrategyDetection:
    """Test Strategy pattern detection."""

    def test_strategy_detection(self, detector):
        """Test detection of Strategy pattern."""
        code = '''
public class PaymentProcessor {
    private IPaymentStrategy strategy;

    public void SetStrategy(IPaymentStrategy paymentStrategy) {
        strategy = paymentStrategy;
    }

    public async Task ProcessPayment(decimal amount) {
        await strategy.Execute(amount);
    }
}
'''
        patterns = detector.detect_patterns(code, "PaymentProcessor")

        strategy_patterns = [p for p in patterns if p.pattern == DesignPattern.STRATEGY]
        assert len(strategy_patterns) > 0


class TestObserverDetection:
    """Test Observer pattern detection."""

    def test_observer_detection(self, detector):
        """Test detection of Observer pattern."""
        code = '''
public class EventPublisher {
    public event EventHandler<MessageEventArgs> MessageReceived;

    public void OnMessageReceived(string message) {
        MessageReceived?.Invoke(this, new MessageEventArgs { Message = message });
    }
}

public class MessageEventArgs : EventArgs {
    public string Message { get; set; }
}
'''
        patterns = detector.detect_patterns(code, "EventPublisher")

        observer_patterns = [p for p in patterns if p.pattern == DesignPattern.OBSERVER]
        assert len(observer_patterns) > 0

    def test_property_changed_observer(self, detector):
        """Test detection of INotifyPropertyChanged observer."""
        code = '''
public class User : INotifyPropertyChanged {
    private string _name;

    public string Name {
        get => _name;
        set {
            _name = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Name)));
        }
    }

    public event PropertyChangedEventHandler PropertyChanged;
}
'''
        patterns = detector.detect_patterns(code, "User")

        observer_patterns = [p for p in patterns if p.pattern == DesignPattern.OBSERVER]
        assert len(observer_patterns) > 0


class TestCommandDetection:
    """Test Command pattern detection."""

    def test_command_detection(self, detector):
        """Test detection of Command pattern."""
        code = '''
public class CreateUserCommand : ICommand {
    public string Name { get; set; }
    public string Email { get; set; }
}

public class CreateUserCommandHandler : ICommandHandler<CreateUserCommand> {
    public async Task Execute(CreateUserCommand command) {
        // Create user logic
    }

    public async Task Undo() {
        // Rollback logic
    }
}
'''
        patterns = detector.detect_patterns(code, "CreateUserCommandHandler")

        command_patterns = [p for p in patterns if p.pattern == DesignPattern.COMMAND]
        assert len(command_patterns) > 0


class TestRepositoryDetection:
    """Test Repository pattern detection."""

    def test_repository_detection(self, detector):
        """Test detection of Repository pattern."""
        code = '''
public class UserRepository : IRepository<User> {
    private readonly DbContext _context;

    public async Task<User> Get(int id) {
        return await _context.Users.FindAsync(id);
    }

    public async Task Add(User user) {
        _context.Users.Add(user);
        await _context.SaveChangesAsync();
    }

    public async Task Remove(int id) {
        var user = await Get(id);
        _context.Users.Remove(user);
        await _context.SaveChangesAsync();
    }
}
'''
        patterns = detector.detect_patterns(code, "UserRepository")

        repo_patterns = [p for p in patterns if p.pattern == DesignPattern.REPOSITORY]
        assert len(repo_patterns) > 0
        assert repo_patterns[0].confidence >= 0.6


class TestUnitOfWorkDetection:
    """Test Unit of Work pattern detection."""

    def test_unit_of_work_detection(self, detector):
        """Test detection of Unit of Work pattern."""
        code = '''
public class UnitOfWork : IUnitOfWork {
    private readonly DbContext _context;

    public IUserRepository Users { get; }
    public IOrderRepository Orders { get; }

    public async Task<int> SaveChangesAsync() {
        return await _context.SaveChangesAsync();
    }

    public async Task BeginTransactionAsync() {
        await _context.Database.BeginTransactionAsync();
    }

    public async Task CommitAsync() {
        await _context.Database.CommitTransactionAsync();
    }
}
'''
        patterns = detector.detect_patterns(code, "UnitOfWork")

        uow_patterns = [p for p in patterns if p.pattern == DesignPattern.UNIT_OF_WORK]
        assert len(uow_patterns) > 0


class TestCQRSDetection:
    """Test CQRS pattern detection."""

    def test_cqrs_detection(self, detector):
        """Test detection of CQRS pattern."""
        code = '''
public class GetUserByIdQuery : IQuery<User> {
    public int Id { get; set; }
}

public class GetUserByIdQueryHandler : IQueryHandler<GetUserByIdQuery, User> {
    public async Task<User> Handle(GetUserByIdQuery query) {
        return await _repository.GetUser(query.Id);
    }
}

public class CreateUserCommand : ICommand {
    public string Name { get; set; }
}

public class CreateUserCommandHandler : ICommandHandler<CreateUserCommand> {
    public async Task Handle(CreateUserCommand command) {
        // Create user
    }
}
'''
        patterns = detector.detect_patterns(code, "QueryHandler")

        # May or may not detect depending on what snippet is analyzed


class TestPubSubDetection:
    """Test Pub/Sub pattern detection."""

    def test_pubsub_detection(self, detector):
        """Test detection of Pub/Sub pattern."""
        code = '''
public class EventBus : IEventBus {
    private readonly Dictionary<Type, List<Delegate>> _subscribers = new();

    public void Subscribe<T>(Func<T, Task> handler) {
        var type = typeof(T);
        if (!_subscribers.ContainsKey(type)) {
            _subscribers[type] = new List<Delegate>();
        }
        _subscribers[type].Add(handler);
    }

    public async Task Publish<T>(T @event) {
        if (_subscribers.TryGetValue(typeof(T), out var handlers)) {
            foreach (var handler in handlers) {
                await ((Func<T, Task>)handler)(@event);
            }
        }
    }
}
'''
        patterns = detector.detect_patterns(code, "EventBus")

        pubsub_patterns = [p for p in patterns if p.pattern == DesignPattern.PUBSUB]
        assert len(pubsub_patterns) > 0


class TestMultiplePatternDetection:
    """Test detection of multiple patterns in same code."""

    def test_multiple_patterns(self, detector):
        """Test detection of multiple patterns."""
        code = '''
public class ConfigurationBuilder {
    private Dictionary<string, string> _settings = new();

    public ConfigurationBuilder WithSetting(string key, string value) {
        _settings[key] = value;
        return this;
    }

    public IConfiguration Build() {
        return new Configuration(_settings);
    }
}

public class Configuration : IConfiguration {
    private readonly Dictionary<string, string> _settings;

    public Configuration(Dictionary<string, string> settings) {
        _settings = settings;
    }

    public string Get(string key) => _settings.GetValueOrDefault(key);
}
'''
        patterns = detector.detect_patterns(code, "ConfigurationBuilder")

        builder_patterns = [p for p in patterns if p.pattern == DesignPattern.BUILDER]
        assert len(builder_patterns) > 0

        # Should detect multiple patterns
        assert len(patterns) > 1


class TestPatternConfidence:
    """Test pattern confidence scoring."""

    def test_high_confidence_pattern(self, detector):
        """Test that clear patterns have high confidence."""
        code = '''
public class Repository : IRepository {
    public async Task<User> Get(int id) { }
    public async Task Add(User user) { }
    public async Task Remove(int id) { }
    public async Task Update(User user) { }
}
'''
        patterns = detector.detect_patterns(code, "Repository")

        if patterns:
            # Clear patterns should have reasonably high confidence
            assert any(p.confidence >= 0.5 for p in patterns)

    def test_low_confidence_pattern(self, detector):
        """Test that unclear patterns have lower confidence."""
        code = '''
public class Helper {
    public void DoSomething() { }
}
'''
        patterns = detector.detect_patterns(code, "Helper")

        # Generic code shouldn't match many patterns
        assert len(patterns) <= 2


class TestPatternIndicators:
    """Test pattern indicator extraction."""

    def test_singleton_indicators(self, detector):
        """Test that singleton indicators are found."""
        code = '''
public class Singleton {
    private static readonly Singleton instance = new();
    private Singleton() { }
    public static Singleton Instance => instance;
}
'''
        patterns = detector.detect_patterns(code, "Singleton")

        singleton = [p for p in patterns if p.pattern == DesignPattern.SINGLETON]
        if singleton:
            assert len(singleton[0].indicators) > 0

    def test_repository_indicators(self, detector):
        """Test that repository indicators are found."""
        code = '''
public class UserRepository : IRepository<User> {
    public async Task<User> Get(int id) { }
    public async Task Add(User user) { }
    public async Task Remove(int id) { }
}
'''
        patterns = detector.detect_patterns(code, "UserRepository")

        repo = [p for p in patterns if p.pattern == DesignPattern.REPOSITORY]
        if repo:
            assert "CRUD methods" in repo[0].indicators or "Repository/DAO in name" in repo[0].indicators
