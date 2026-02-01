"""Tests for CSharpCodeParser utility."""

from csharp_code_parser import BraceFindMode, BraceFindResult, CSharpCodeParser


class TestBraceFindingBasic:
    """Test basic brace-finding functionality."""

    def test_find_block_end_simple_braces(self):
        """BraceFinding_SimpleBraces_FindsClosingBrace

        Basic test: find closing brace in simple code block.
        """
        code = "public void Method() {\n    Console.WriteLine();\n}"
        result = CSharpCodeParser.find_block_end(
            code, 19, BraceFindMode.WAIT_FOR_OPENING
        )

        assert result.success
        assert result.end_position > 0
        assert result.reason is None

    def test_find_block_end_nested_braces(self):
        """BraceFinding_NestedBraces_CountsCorrectly

        Test that nested braces are handled correctly.
        """
        code = "{\n    {\n        Console.WriteLine();\n    }\n}"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_comments_single_line(self):
        """BraceFinding_SingleLineComment_IgnoresBracesInComment

        Braces inside single-line comments should not be counted.
        """
        code = "{\n    // This is a comment with } inside\n    int x = 5;\n}"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_comments_multi_line(self):
        """BraceFinding_MultiLineComment_IgnoresBracesInComment

        Braces inside multi-line comments should not be counted.
        """
        code = "{\n    /* Comment with } and { inside */\n    int x = 5;\n}"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_string_containing_braces(self):
        """BraceFinding_StringWithBraces_IgnoresInternalBraces

        Braces inside strings should not be counted.
        """
        code = '{\n    string s = "This has } and { inside";\n    int x = 5;\n}'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_verbatim_string(self):
        """BraceFinding_VerbatimString_IgnoresBraces

        Braces inside verbatim strings should not be counted.
        """
        code = '{\n    string s = @"Path: C:\\ {folder} \\ file";\n    int x = 5;\n}'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_verbatim_string_escaped_quotes(self):
        """BraceFinding_VerbatimStringEscapedQuotes_HandlesDoubleQuotes

        Escaped quotes ("") in verbatim strings should not end the string.
        """
        code = '{\n    string s = @"He said ""Hello"" and went inside { the block }";\n    int x = 5;\n}'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_char_literal(self):
        """BraceFinding_CharLiteral_IgnoresBrace

        Braces inside character literals should not be counted.
        """
        code = "{\n    char c = '{';\n    int x = 5;\n}"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_find_block_end_with_escaped_char_in_string(self):
        """BraceFinding_EscapedCharInString_IgnoresEscapeInBrace

        Test that escaped characters inside strings don't confuse parser.
        """
        code = r'{ string s = "He said \"Hello\" with } brace"; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None


class TestBraceFindingModes:
    """Test different modes of brace finding."""

    def test_immediate_mode_starts_counting_immediately(self):
        """BraceFinding_ImmediateMode_StartsCounting

        IMMEDIATE mode should start counting from first brace.
        """
        code = "public void Method() {\n    int x = 5;\n}"
        result = CSharpCodeParser.find_block_end(code, 19, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_wait_for_opening_mode_skips_to_first_brace(self):
        """BraceFinding_WaitForOpeningMode_SkipsUntilFirstBrace

        WAIT_FOR_OPENING mode should skip until first { is found.
        """
        code = "public void Method()\n{\n    int x = 5;\n}"
        result = CSharpCodeParser.find_block_end(
            code, 0, BraceFindMode.WAIT_FOR_OPENING
        )

        assert result.success

    def test_wait_for_opening_finds_first_brace_before_counting(self):
        """BraceFinding_WaitForOpeningSkipsText_ThenCounts

        WAIT_FOR_OPENING should find the first { before starting count.
        """
        code = "// Comment with } brace\n{\n    int x = 5;\n}"
        result = CSharpCodeParser.find_block_end(
            code, 0, BraceFindMode.WAIT_FOR_OPENING
        )

        assert result.success


class TestBraceFindingLineBased:
    """Test brace finding with line-based input."""

    def test_find_block_end_with_line_list(self):
        """BraceFinding_LineList_ReturnsLineNumber

        When given lines as list, should return line number not char position.
        """
        lines = ["public void Method() {", "    Console.WriteLine();", "}"]
        result = CSharpCodeParser.find_block_end(lines, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        # Result should be line number 2 (the closing brace line)
        assert result.end_position == 2

    def test_find_block_end_line_based_with_nested(self):
        """BraceFinding_LineBasedNested_CountsAcrossLines

        Line-based finding should properly count nested braces across lines.
        """
        lines = ["{", "    {", "        int x = 5;", "    }", "}"]
        result = CSharpCodeParser.find_block_end(lines, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.end_position == 4


class TestBraceFindingEdgeCases:
    """Test edge cases and error conditions."""

    def test_find_block_end_empty_code(self):
        """BraceFinding_EmptyCode_Fails

        Empty code should fail gracefully.
        """
        code = ""
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert not result.success
        assert result.reason is not None

    def test_find_block_end_unmatched_opening_brace(self):
        """BraceFinding_UnmatchedOpeningBrace_Fails

        Code with opening brace but no closing should fail.
        """
        code = "public void Method() {\n    int x = 5;"
        result = CSharpCodeParser.find_block_end(code, 19, BraceFindMode.IMMEDIATE)

        assert not result.success
        assert "End of content" in result.reason or "Exceeded" in result.reason

    def test_find_block_end_no_opening_brace_wait_mode(self):
        """BraceFinding_NoOpeningBraceWaitMode_Fails

        WAIT_FOR_OPENING mode with no opening brace should fail.
        """
        code = "int x = 5;"
        result = CSharpCodeParser.find_block_end(
            code, 0, BraceFindMode.WAIT_FOR_OPENING
        )

        assert not result.success

    def test_find_block_end_max_iterations_exceeded(self):
        """BraceFinding_MaxIterationsExceeded_FailsGracefully

        Should fail gracefully when max iterations reached.
        """
        code = "{ " + " " * 600_000  # Very long code
        result = CSharpCodeParser.find_block_end(
            code, 0, BraceFindMode.IMMEDIATE, max_iterations=1000
        )

        assert not result.success
        assert "Exceeded max iterations" in result.reason

    def test_find_block_end_start_beyond_content(self):
        """BraceFinding_StartBeyondContent_HandlesGracefully

        Start position beyond content length should handle gracefully.
        """
        code = "{ int x = 5; }"
        result = CSharpCodeParser.find_block_end(code, 1000, BraceFindMode.IMMEDIATE)

        # Should either fail or use fallback
        assert isinstance(result, BraceFindResult)


class TestBraceFindingComments:
    """Test complex comment handling scenarios."""

    def test_nested_comment_like_patterns_in_string(self):
        """BraceFinding_NestedCommentPatternsInString_IgnoresPatterns

        Comment delimiters inside strings should be ignored.
        """
        code = '{ string s = "/* This looks like comment */ with { brace"; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_comment_line_ending_in_string(self):
        """BraceFinding_CommentLineEndingInString_IgnoresPattern

        // comment marker inside string should be ignored.
        """
        code = '{ string s = "Path: C://Server/Folder/File { with brace"; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_multiline_comment_with_nested_braces(self):
        """BraceFinding_MultilineCommentNestedBraces_IgnoresAll

        All braces inside multi-line comment should be ignored.
        """
        code = (
            "{ /* Comment\n    with { nested } braces\n    and more }\n*/ int x = 5; }"
        )
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success


class TestBraceFindingStrings:
    """Test complex string handling scenarios."""

    def test_string_with_escaped_quote_at_end(self):
        """BraceFinding_StringEscapedQuoteAtEnd_ContinuesString

        Escaped quote at string end should not end the string.
        """
        code = r'{ string s = "He said \"Hello\" and left }"; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_multiple_strings_with_braces(self):
        """BraceFinding_MultipleStringsWithBraces_IgnoresAll

        Multiple strings each with braces should all be ignored.
        """
        code = '{ string s1 = "{1}"; string s2 = "{2}"; int x = 5; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_verbatim_string_with_backslash_quote(self):
        """BraceFinding_VerbatimStringBackslashQuote_HandlesEscaping

        Verbatim strings with special escaping should work.
        """
        code = r'{ string s = @"C:\path\to\{folder}"; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_string_with_newline_escape(self):
        """BraceFinding_StringNewlineEscape_IgnoresNewlineCharacter

        String with \\n escape sequence should be handled correctly.
        """
        code = '{ string s = "Line1\\nLine2 with } brace"; }'
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success


class TestBraceFindingCharLiterals:
    """Test character literal handling."""

    def test_char_literal_opening_brace(self):
        """BraceFinding_CharOpeningBrace_IgnoresBrace

        Character literal '{' should not be counted as opening brace.
        """
        code = "{ char c = '{'; int x = 5; }"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_char_literal_closing_brace(self):
        """BraceFinding_CharClosingBrace_IgnoresBrace

        Character literal '}' should not be counted as closing brace.
        """
        code = "{ char c = '}'; int x = 5; }"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success

    def test_char_literal_escaped_quote(self):
        """BraceFinding_CharEscapedQuote_HandlesEscape

        Character literal with escaped quote should be handled.
        """
        code = "{ char c = '\\''; int x = 5; }"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success


class TestBraceFindingRealWorldCode:
    """Test with realistic C# code patterns."""

    def test_real_world_class_with_methods(self):
        """BraceFinding_RealWorldClass_FindsEnd

        Real-world class definition with methods.
        """
        code = """public class MyService
{
    private readonly IRepository _repo;

    public MyService(IRepository repo)
    {
        _repo = repo;
    }

    public void DoWork()
    {
        var result = _repo.GetData();
        Console.WriteLine($"Result: {result}");
    }
}"""
        result = CSharpCodeParser.find_block_end(
            code, code.index("{"), BraceFindMode.IMMEDIATE
        )

        assert result.success

    def test_real_world_linq_query(self):
        """BraceFinding_RealWorldLINQ_IgnoresCurlyBracesInStringFormatting

        LINQ with string formatting containing braces.
        """
        code = """var query = data
    .Where(x => x.IsActive)
    .Select(x => new {
        x.Id,
        x.Name,
        Message = $"Item {x.Id}: {x.Name}"
    });"""
        # This should handle the anonymous type braces correctly
        first_brace = code.index("{")
        result = CSharpCodeParser.find_block_end(
            code, first_brace, BraceFindMode.IMMEDIATE
        )

        # Should find the first closing brace of the anonymous type
        assert isinstance(result, BraceFindResult)

    def test_real_world_dictionary_initializer(self):
        """BraceFinding_DictionaryInitializer_IgnoresBraces

        Dictionary initializer with nested braces in string values.
        """
        code = """var dict = new Dictionary<string, string>
{
    { "key1", "value with } brace" },
    { "key2", "another { value" }
};"""
        first_brace = code.index("{")
        result = CSharpCodeParser.find_block_end(
            code, first_brace, BraceFindMode.IMMEDIATE
        )

        assert result.success


class TestBraceFindingResultStructure:
    """Test BraceFindResult structure and values."""

    def test_result_success_has_no_reason(self):
        """BraceFindResult_SuccessCase_NoReason

        Successful result should have None reason.
        """
        code = "{ int x = 5; }"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.reason is None

    def test_result_failure_has_reason(self):
        """BraceFindResult_FailureCase_HasReason

        Failed result should have a reason.
        """
        code = "{ int x = 5"  # Missing closing brace
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert not result.success
        assert result.reason is not None
        assert len(result.reason) > 0

    def test_result_end_position_is_positive_on_success(self):
        """BraceFindResult_SuccessEndPosition_IsValid

        Successful result should have valid end position.
        """
        code = "{ int x = 5; }"
        result = CSharpCodeParser.find_block_end(code, 0, BraceFindMode.IMMEDIATE)

        assert result.success
        assert result.end_position >= 0
        assert result.end_position <= len(code)
