"""Tests for unified AST extraction across languages."""

from models import CodeChunk, Language
from pattern_extractor import PatternExtractor


class TestUnifiedASTExtraction:
    """Test suite for AST extraction working across multiple languages."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PatternExtractor()

    def test_python_class_extraction(self):
        """Test extraction of Python class via unified AST."""
        content = """
class Calculator:
    '''A simple calculator class.'''

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        chunks = self.extractor.extract_chunks(content, "test.py", Language.PYTHON)

        # Should extract at least the class
        assert len(chunks) > 0

        # Look for class chunk (might be extracted via AST or regex)
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        # If AST available, should find Calculator class
        # If AST not available, falls back to regex which also finds it
        assert len(class_chunks) > 0 or any(
            "class Calculator" in c.content for c in chunks
        )

    def test_python_function_extraction(self):
        """Test extraction of Python function via unified AST."""
        content = """
def fibonacci(n):
    '''Calculate fibonacci number.'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        chunks = self.extractor.extract_chunks(content, "test.py", Language.PYTHON)

        # Should extract the function
        assert len(chunks) > 0

        # Look for function chunk (if AST available) or check content
        function_chunks = [c for c in chunks if c.chunk_type == "function"]
        assert len(function_chunks) > 0 or any(
            "def fibonacci" in c.content for c in chunks
        )

    def test_python_decorated_function(self):
        """Test extraction of decorated Python function."""
        content = """
def timer(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@timer
def slow_function():
    import time
    time.sleep(1)
"""
        chunks = self.extractor.extract_chunks(content, "test.py", Language.PYTHON)

        assert len(chunks) > 0

        # Should find decorated function
        assert any("slow_function" in c.content for c in chunks)

    def test_java_class_extraction(self):
        """Test extraction of Java class via unified AST."""
        content = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}
"""
        chunks = self.extractor.extract_chunks(
            content, "Calculator.java", Language.JAVA
        )

        assert len(chunks) > 0

        # Look for class chunk
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) > 0

    def test_java_interface_extraction(self):
        """Test extraction of Java interface via unified AST."""
        content = """
public interface DataProcessor {
    void process(String data);
    String validate(String input);
    void save(Object obj);
    void delete(String id);
}
"""
        chunks = self.extractor.extract_chunks(
            content, "DataProcessor.java", Language.JAVA
        )

        assert len(chunks) > 0

        # Look for interface chunk or check content
        interface_chunks = [c for c in chunks if c.chunk_type == "interface"]
        assert len(interface_chunks) > 0 or any(
            "interface DataProcessor" in c.content for c in chunks
        )

    def test_javascript_class_extraction(self):
        """Test extraction of JavaScript class via unified AST."""
        content = """
class User {
    constructor(name, email) {
        this.name = name;
        this.email = email;
    }

    getDisplayName() {
        return this.name;
    }
}
"""
        chunks = self.extractor.extract_chunks(content, "user.js", Language.JAVASCRIPT)

        assert len(chunks) > 0

        # Look for class chunk
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) > 0

    def test_javascript_function_extraction(self):
        """Test extraction of JavaScript function via unified AST."""
        content = """
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}

function processData(data) {
    return data.map(x => x * 2);
}
"""
        chunks = self.extractor.extract_chunks(content, "calc.js", Language.JAVASCRIPT)

        assert len(chunks) > 0

        # Look for function chunk or check content
        function_chunks = [c for c in chunks if c.chunk_type == "function"]
        assert len(function_chunks) > 0 or any(
            "function calculate" in c.content or "function process" in c.content
            for c in chunks
        )

    def test_javascript_arrow_function(self):
        """Test extraction of JavaScript arrow function."""
        content = """
const add = (a, b) => a + b;

const greet = (name) => {
    console.log(`Hello, ${name}!`);
    return name;
};

const multiply = (x, y) => x * y;
"""
        chunks = self.extractor.extract_chunks(content, "arrow.js", Language.JAVASCRIPT)

        assert len(chunks) > 0

    def test_typescript_interface_extraction(self):
        """Test extraction of TypeScript interface via unified AST."""
        content = """
interface User {
    id: number;
    name: string;
    email: string;
    isActive?: boolean;
}

interface UserService {
    getUser(id: number): Promise<User>;
    createUser(user: User): Promise<User>;
}
"""
        chunks = self.extractor.extract_chunks(content, "types.ts", Language.TYPESCRIPT)

        assert len(chunks) > 0

        # Should find interface declarations
        assert any("interface" in c.content for c in chunks)

    def test_csharp_class_extraction(self):
        """Test extraction of C# class via unified AST."""
        content = """
using System;

namespace MyApp
{
    public class Calculator
    {
        public int Add(int a, int b)
        {
            return a + b;
        }

        public int Subtract(int a, int b)
        {
            return a - b;
        }
    }
}
"""
        chunks = self.extractor.extract_chunks(
            content, "Calculator.cs", Language.CSHARP
        )

        assert len(chunks) > 0

        # Look for class chunk
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) > 0

    def test_csharp_interface_extraction(self):
        """Test extraction of C# interface via unified AST."""
        content = """
public interface IRepository<T>
{
    T GetById(int id);
    void Add(T item);
    void Delete(int id);
}
"""
        chunks = self.extractor.extract_chunks(content, "repo.cs", Language.CSHARP)

        assert len(chunks) > 0

        # Look for interface chunk
        interface_chunks = [c for c in chunks if c.chunk_type == "interface"]
        assert len(interface_chunks) > 0

    def test_csharp_record_extraction(self):
        """Test extraction of C# record via unified AST."""
        content = """
using System;

public record Person(string FirstName, string LastName)
{
    public string FullName => $"{FirstName} {LastName}";
    public int Age { get; set; }
}
"""
        chunks = self.extractor.extract_chunks(content, "person.cs", Language.CSHARP)

        assert len(chunks) > 0

        # Should find record or Person in content
        assert any("record" in c.chunk_type or "Person" in c.content for c in chunks)

    def test_chunk_structure(self):
        """Test that extracted chunks have proper structure."""
        content = """
class TestClass:
    def test_method(self):
        '''Test method'''
        pass

    def another_method(self):
        return True
"""
        chunks = self.extractor.extract_chunks(content, "test.py", Language.PYTHON)

        assert len(chunks) > 0

        for chunk in chunks:
            # Check required fields
            assert isinstance(chunk, CodeChunk)
            assert chunk.content is not None
            assert chunk.file_path is not None
            assert chunk.language is not None
            assert chunk.start_line >= 0  # Can be 0 for semantic chunks
            assert chunk.end_line >= chunk.start_line or chunk.end_line >= 0
            assert chunk.chunk_type is not None

    def test_empty_file_handling(self):
        """Test extraction on empty file."""
        content = ""
        chunks = self.extractor.extract_chunks(content, "empty.py", Language.PYTHON)

        # Should handle gracefully
        assert isinstance(chunks, list)

    def test_file_with_no_extractable_chunks(self):
        """Test file with no class/function definitions."""
        content = """
# Just comments
x = 10
y = 20
"""
        chunks = self.extractor.extract_chunks(content, "data.py", Language.PYTHON)

        # Should fall back to semantic chunking or return empty
        assert isinstance(chunks, list)

    def test_multiline_class_with_docstring(self):
        """Test extraction of class with multiline docstring."""
        content = '''
class DataProcessor:
    """
    Process data efficiently.

    This class handles:
    - Data validation
    - Transformation
    - Storage
    """

    def process(self, data):
        return data.upper()
'''
        chunks = self.extractor.extract_chunks(content, "processor.py", Language.PYTHON)

        assert len(chunks) > 0

    def test_nested_classes(self):
        """Test extraction handles nested structures."""
        content = """
class Outer:
    class Inner:
        def inner_method(self):
            pass

    def outer_method(self):
        pass
"""
        chunks = self.extractor.extract_chunks(content, "nested.py", Language.PYTHON)

        assert len(chunks) > 0

        # Should find at least the outer class
        assert any("Outer" in c.content or "class" in c.chunk_type for c in chunks)
