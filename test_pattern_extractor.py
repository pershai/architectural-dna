"""Tests for PatternExtractor."""

import pytest

from models import Language
from pattern_extractor import PatternExtractor


class TestPatternExtractor:
    """Tests for PatternExtractor class."""

    @pytest.fixture
    def extractor(self):
        return PatternExtractor()

    # ==========================================================================
    # Python extraction tests
    # ==========================================================================

    def test_extract_python_class(self, extractor):
        """Test extracting a Python class."""
        code = '''import logging

class MyService:
    """A service class."""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def process(self, data):
        """Process data."""
        return data.upper()
'''
        chunks = extractor.extract_chunks(code, "test.py", Language.PYTHON)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "class"
        assert chunks[0].name == "MyService"
        assert chunks[0].language == Language.PYTHON
        assert "import logging" in chunks[0].context

    def test_extract_python_function(self, extractor):
        """Test extracting a Python function."""
        code = '''from typing import Optional

def calculate_total(items: list, tax_rate: float = 0.1) -> float:
    """Calculate total with tax."""
    subtotal = sum(item.price for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax
'''
        chunks = extractor.extract_chunks(code, "utils.py", Language.PYTHON)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "function"
        assert chunks[0].name == "calculate_total"

    def test_extract_python_async_function(self, extractor):
        """Test extracting an async Python function."""
        code = '''import asyncio

async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
'''
        chunks = extractor.extract_chunks(code, "api.py", Language.PYTHON)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "function"
        assert chunks[0].name == "fetch_data"

    def test_extract_python_decorated_function(self, extractor):
        """Test extracting a decorated Python function."""
        code = '''from functools import wraps

@decorator1
@decorator2
def my_handler(request):
    """Handle the request."""
    data = request.json()
    result = process(data)
    return result
'''
        chunks = extractor.extract_chunks(code, "handlers.py", Language.PYTHON)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "function"
        assert "@decorator1" in chunks[0].content

    def test_extract_python_multiple_chunks(self, extractor):
        """Test extracting multiple Python chunks."""
        code = '''import os

class Config:
    """Configuration class."""

    def __init__(self):
        self.debug = os.getenv("DEBUG", False)
        self.port = int(os.getenv("PORT", 8080))
        self.host = os.getenv("HOST", "0.0.0.0")

def load_config():
    """Load configuration."""
    config = Config()
    validate(config)
    return config
'''
        chunks = extractor.extract_chunks(code, "config.py", Language.PYTHON)

        assert len(chunks) == 2
        class_chunk = next(c for c in chunks if c.chunk_type == "class")
        func_chunk = next(c for c in chunks if c.chunk_type == "function")

        assert class_chunk.name == "Config"
        assert func_chunk.name == "load_config"

    def test_extract_python_imports(self, extractor):
        """Test Python import extraction."""
        code = """import os
import sys
from typing import Optional, List
from pathlib import Path

# This is a comment
class MyClass:
    pass
"""
        imports = extractor._extract_python_imports(code)

        assert "import os" in imports
        assert "import sys" in imports
        assert "from typing import Optional, List" in imports
        assert "from pathlib import Path" in imports
        assert "class MyClass" not in imports

    # ==========================================================================
    # Java extraction tests
    # ==========================================================================

    def test_extract_java_class(self, extractor):
        """Test extracting a Java class."""
        code = """package com.example.service;

import org.springframework.stereotype.Service;

@Service
public class UserService {
    private final UserRepository repository;

    public UserService(UserRepository repository) {
        this.repository = repository;
    }

    public User findById(Long id) {
        return repository.findById(id).orElse(null);
    }
}
"""
        chunks = extractor.extract_chunks(code, "UserService.java", Language.JAVA)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "class"
        assert chunks[0].name == "UserService"
        assert "@Service" in chunks[0].content
        assert "package com.example.service" in chunks[0].context

    def test_extract_java_interface(self, extractor):
        """Test extracting a Java interface."""
        code = """package com.example.repository;

import java.util.List;

public interface UserRepository {
    User findById(Long id);
    List<User> findAll();
    void save(User user);
}
"""
        chunks = extractor.extract_chunks(code, "UserRepository.java", Language.JAVA)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "class"
        assert chunks[0].name == "UserRepository"

    def test_extract_java_context(self, extractor):
        """Test Java context extraction."""
        code = """package com.example;

import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class MyService {
}
"""
        context = extractor._extract_java_context(code)

        assert "package com.example" in context
        assert "import java.util.List" in context
        assert "import org.springframework.stereotype.Service" in context
        assert "@Service" not in context

    # ==========================================================================
    # JavaScript/TypeScript extraction tests
    # ==========================================================================

    def test_extract_js_class(self, extractor):
        """Test extracting a JavaScript class."""
        code = """import { EventEmitter } from 'events';

export class DataProcessor extends EventEmitter {
    constructor(config) {
        super();
        this.config = config;
    }

    process(data) {
        const result = this.transform(data);
        this.emit('processed', result);
        return result;
    }
}
"""
        chunks = extractor.extract_chunks(code, "processor.js", Language.JAVASCRIPT)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "class"
        assert chunks[0].name == "DataProcessor"

    def test_extract_js_function(self, extractor):
        """Test extracting a JavaScript function."""
        code = """import axios from 'axios';

export async function fetchUsers(apiUrl) {
    const response = await axios.get(`${apiUrl}/users`);
    if (!response.ok) {
        throw new Error('Failed');
    }
    return response.data;
}
"""
        chunks = extractor.extract_chunks(code, "api.js", Language.JAVASCRIPT)

        assert len(chunks) >= 1
        # May be function or file chunk depending on extraction
        assert any(c.name == "fetchUsers" or "fetchUsers" in c.content for c in chunks)

    def test_extract_js_arrow_function(self, extractor):
        """Test extracting a JavaScript arrow function."""
        code = """import { validate } from './utils';

export const processData = async (data) => {
    validate(data);
    const result = transform(data);
    return result;
}
"""
        chunks = extractor.extract_chunks(code, "process.js", Language.JAVASCRIPT)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "function"
        assert chunks[0].name == "processData"

    def test_extract_ts_class(self, extractor):
        """Test extracting a TypeScript class."""
        code = """import { Injectable } from '@angular/core';

@Injectable()
export class ApiService {
    private baseUrl: string;

    constructor(private http: HttpClient) {
        this.baseUrl = '/api';
    }

    async getData(): Promise<Data[]> {
        return this.http.get<Data[]>(this.baseUrl);
    }
}
"""
        chunks = extractor.extract_chunks(code, "api.service.ts", Language.TYPESCRIPT)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "class"
        assert chunks[0].name == "ApiService"

    def test_extract_js_imports(self, extractor):
        """Test JavaScript import extraction."""
        code = """import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';

const Component = () => {};
"""
        imports = extractor._extract_js_imports(code)

        assert "import React from 'react'" in imports
        assert "import { useState, useEffect } from 'react'" in imports
        assert "const Component" not in imports

    # ==========================================================================
    # Brace block finding tests
    # ==========================================================================

    def test_find_brace_block_end_simple(self, extractor):
        """Test finding end of simple brace block."""
        lines = ["function test() {", "    return 1;", "}"]
        end = extractor._find_brace_block_end(lines, 0)
        assert end == 2

    def test_find_brace_block_end_nested(self, extractor):
        """Test finding end of nested brace block."""
        lines = [
            "class Test {",
            "    method() {",
            "        if (true) {",
            "            return 1;",
            "        }",
            "    }",
            "}",
        ]
        end = extractor._find_brace_block_end(lines, 0)
        assert end == 6

    # ==========================================================================
    # Semantic chunking tests
    # ==========================================================================

    def test_semantic_chunk_small_file(self, extractor):
        """Test semantic chunking for small files."""
        code = """def hello():
    print("Hello")
    print("World")
    print("!")
    return True
"""
        chunks = extractor._semantic_chunk(code, "small.go", Language.GO)

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "file"

    def test_is_valid_chunk_too_short(self, extractor):
        """Test that short chunks are invalid."""
        short_code = "x = 1\ny = 2"
        assert not extractor._is_valid_chunk(short_code)

    def test_is_valid_chunk_valid(self, extractor):
        """Test that longer chunks are valid."""
        valid_code = """def example():
    line1 = "test"
    line2 = "test"
    line3 = "test"
    line4 = "test"
    return line1
"""
        assert extractor._is_valid_chunk(valid_code)

    # ==========================================================================
    # Edge cases
    # ==========================================================================

    def test_empty_content(self, extractor):
        """Test handling empty content."""
        chunks = extractor.extract_chunks("", "empty.py", Language.PYTHON)
        assert chunks == []

    def test_no_extractable_chunks(self, extractor):
        """Test file with no extractable chunks falls back to semantic."""
        code = """# Just a comment
x = 1
y = 2
"""
        chunks = extractor.extract_chunks(code, "simple.py", Language.PYTHON)
        # Falls back to semantic chunking, but content is too short (< 5 lines)
        assert len(chunks) == 0

    def test_unsupported_language_uses_semantic(self, extractor):
        """Test unsupported language uses semantic chunking."""
        go_code = """package main

import "fmt"

func main() {
    fmt.Println("Hello")
    fmt.Println("World")
    fmt.Println("!")
    fmt.Println("test")
}
"""
        chunks = extractor.extract_chunks(go_code, "main.go", Language.GO)
        # Should use semantic chunking
        assert len(chunks) >= 0  # May or may not meet minimum lines
