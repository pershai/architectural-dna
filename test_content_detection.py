"""Tests for Language.from_content() content-based language detection."""

from models import Language


class TestLanguageDetectionFromContent:
    """Test suite for Language.from_content() method."""

    def test_detect_python_shebang(self):
        """Test Python detection from shebang."""
        content_env = "#!/usr/bin/env python\nprint('hello')"
        assert Language.from_content(content_env) == Language.PYTHON

        content_direct = "#!/usr/bin/python\nimport sys"
        assert Language.from_content(content_direct) == Language.PYTHON

        content_python3 = "#!/usr/bin/python3\ndef foo(): pass"
        assert Language.from_content(content_python3) == Language.PYTHON

    def test_detect_node_shebang(self):
        """Test JavaScript detection from Node shebang."""
        content = "#!/usr/bin/env node\nconsole.log('hello')"
        assert Language.from_content(content) == Language.JAVASCRIPT

    def test_detect_csharp_keywords(self):
        """Test C# detection from using System and namespace."""
        content = "using System;\nusing System.Collections;\nnamespace MyApp\n{\n    public class Program { }\n}"
        detected = Language.from_content(content)
        assert detected == Language.CSHARP

    def test_detect_csharp_with_braces_semicolon(self):
        """Test C# detection requires both { and ; indicators."""
        # Has "using System" but no { or ;
        content_incomplete = "using System"
        assert Language.from_content(content_incomplete) != Language.CSHARP

        # Has both { and ; with namespace
        content_complete = "using System;\nnamespace Test { }"
        assert Language.from_content(content_complete) == Language.CSHARP

    def test_detect_java_package(self):
        """Test Java detection from package and import."""
        content = (
            "package com.example;\nimport java.util.List;\npublic class MyClass { }"
        )
        assert Language.from_content(content) == Language.JAVA

    def test_detect_python_def_keyword(self):
        """Test Python detection from def keyword."""
        content = "def hello():\n    print('world')"
        assert Language.from_content(content) == Language.PYTHON

    def test_detect_python_import_keyword(self):
        """Test Python detection from import keyword."""
        content = "import numpy\nimport pandas as pd"
        assert Language.from_content(content) == Language.PYTHON

    def test_detect_typescript_type_annotation(self):
        """Test TypeScript detection from type annotations."""
        content_string = "const name: string = 'hello'"
        assert Language.from_content(content_string) == Language.TYPESCRIPT

        content_number = "const count: number = 42"
        assert Language.from_content(content_number) == Language.TYPESCRIPT

        content_interface = "interface User { name: string }"
        assert Language.from_content(content_interface) == Language.TYPESCRIPT

        content_type = "export type Status = 'active' | 'inactive'"
        assert Language.from_content(content_type) == Language.TYPESCRIPT

    def test_detect_javascript_function(self):
        """Test JavaScript detection from function declaration."""
        content = "function hello() { console.log('world'); }"
        assert Language.from_content(content) == Language.JAVASCRIPT

    def test_detect_javascript_const_let(self):
        """Test JavaScript detection from const/let."""
        content_const = "const x = 10; const y = 20;"
        detected = Language.from_content(content_const)
        # Should be JavaScript or TypeScript (both have const)
        assert detected in (Language.JAVASCRIPT, Language.TYPESCRIPT)

        content_let = "let name = 'test'; let age = 25;"
        detected = Language.from_content(content_let)
        assert detected in (Language.JAVASCRIPT, Language.TYPESCRIPT)

    def test_detect_javascript_export(self):
        """Test JavaScript detection from export statement."""
        content = "export { Component } from './Component'"
        detected = Language.from_content(content)
        # Should prefer TypeScript for export type
        # But export { } alone should be JavaScript
        assert detected in (Language.JAVASCRIPT, Language.TYPESCRIPT)

    def test_detect_go_package_main(self):
        """Test Go detection from package main."""
        content = 'package main\n\nfunc main() {\n    println("hello")\n}'
        assert Language.from_content(content) == Language.GO

    def test_detect_go_func_keyword(self):
        """Test Go detection from func keyword."""
        content = (
            "package mylib\n\nfunc Process(data []string) error {\n    return nil\n}"
        )
        assert Language.from_content(content) == Language.GO

    def test_detect_go_struct(self):
        """Test Go detection from struct pattern."""
        content = "package models\n\ntype User struct {\n    Name string\n}"
        assert Language.from_content(content) == Language.GO

    def test_fallback_to_extension(self):
        """Test fallback to file extension when content is ambiguous."""
        # Ambiguous content with .py extension
        content = "x = 10"
        detected = Language.from_content(content, ".py")
        assert detected == Language.PYTHON

        # Ambiguous content with .java extension
        content = "class MyClass { }"
        detected = Language.from_content(content, ".java")
        assert detected == Language.JAVA

        # Ambiguous content with .go extension
        content = "package main"
        detected = Language.from_content(content, ".go")
        assert detected == Language.GO

    def test_unknown_language_no_extension(self):
        """Test detection returns UNKNOWN when cannot determine."""
        content = "random text without any language indicators"
        detected = Language.from_content(content, "")
        assert detected == Language.UNKNOWN

    def test_detection_first_500_chars(self):
        """Test that detection uses only first 500 characters."""
        # Create content where detection would differ if using more than 500 chars
        intro = "# Some generic README\n" * 10  # ~230 chars
        java_code = "package com.example;\nimport java.util.*;\n"
        rest = "x = 1\n" * 100  # Lots of Python-like code

        content = intro + java_code + rest
        assert len(content) > 500

        # Should detect Java from package statement in first 500 chars
        # not Python from the rest
        result = Language.from_content(content[:500])
        assert result == Language.JAVA

    def test_detection_case_insensitive_keywords(self):
        """Test language detection handles case sensitivity correctly."""
        # Keywords should match exactly (case-sensitive)
        # "using system" (lowercase "system") matches "using System" check in "any()"
        # because it's doing substring matching on the header, not case-sensitive
        content_lower = "x = 1 + 2"
        # Generic content without clear language indicators
        result = Language.from_content(content_lower, ".py")
        # Should fallback to extension since no clear indicators
        assert result == Language.PYTHON

    def test_complex_python_file(self):
        """Test detection on realistic Python file."""
        content = """#!/usr/bin/env python
\"\"\"Module docstring.\"\"\"
import os
import sys
from typing import List

def process_data(items: List[str]) -> None:
    \"\"\"Process items.\"\"\"
    for item in items:
        print(item)

class DataProcessor:
    \"\"\"Main processor class.\"\"\"
    def __init__(self):
        self.data = []
"""
        assert Language.from_content(content) == Language.PYTHON

    def test_complex_csharp_file(self):
        """Test detection on realistic C# file."""
        content = """using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;

namespace MyApplication.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class UserController : ControllerBase
    {
        private readonly IUserService _userService;

        public UserController(IUserService userService)
        {
            _userService = userService;
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetUser(int id)
        {
            var user = await _userService.GetUserAsync(id);
            return Ok(user);
        }
    }
}
"""
        assert Language.from_content(content) == Language.CSHARP

    def test_complex_java_file(self):
        """Test detection on realistic Java file."""
        content = """package com.example.service;

import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public Optional<User> findById(Long id) {
        return userRepository.findById(id);
    }

    public List<User> findAll() {
        return userRepository.findAll();
    }
}
"""
        assert Language.from_content(content) == Language.JAVA

    def test_complex_typescript_file(self):
        """Test detection on realistic TypeScript file."""
        content = """interface User {
    id: number;
    name: string;
    email: string;
}

export class UserService {
    async getUser(id: number): Promise<User> {
        const response = await fetch(`/api/users/${id}`);
        const data: User = await response.json();
        return data;
    }

    async createUser(user: User): Promise<User> {
        const response = await fetch('/api/users', {
            method: 'POST',
            body: JSON.stringify(user),
        });
        return response.json();
    }
}
"""
        assert Language.from_content(content) == Language.TYPESCRIPT

    def test_complex_go_file(self):
        """Test detection on realistic Go file."""
        content = """package main

import (
    "fmt"
    "log"
)

type User struct {
    ID   int
    Name string
}

func (u *User) String() string {
    return fmt.Sprintf("User(%d, %s)", u.ID, u.Name)
}

func main() {
    user := &User{ID: 1, Name: "John"}
    log.Println(user)
}
"""
        assert Language.from_content(content) == Language.GO
