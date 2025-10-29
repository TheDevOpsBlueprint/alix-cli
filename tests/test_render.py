import pytest
from unittest.mock import patch, MagicMock
from rich.table import Table
from rich.text import Text
from alix.render import Render


class TestRender:
    @pytest.fixture
    def render(self):
        return Render()

    def test_split_keep_ws_basic_splitting(self, render):
        result = render._split_keep_ws("hello world")
        expected = ["hello", " ", "world"]
        assert result == expected

    def test_split_keep_ws_multiple_spaces(self, render):
        result = render._split_keep_ws("a   b")
        expected = ["a", "   ", "b"]
        assert result == expected

    def test_split_keep_ws_tabs_and_newlines(self, render):
        result = render._split_keep_ws("a\tb\nc")
        expected = ["a", "\t", "b", "\n", "c"]
        assert result == expected

    def test_split_keep_ws_no_whitespace(self, render):
        result = render._split_keep_ws("hello")
        expected = ["hello"]
        assert result == expected

    def test_split_keep_ws_empty_string(self, render):
        result = render._split_keep_ws("")
        expected = [""]
        assert result == expected

    def test_split_keep_ws_mixed_whitespace(self, render):
        result = render._split_keep_ws("x  y\tz\nw")
        expected = ["x", "  ", "y", "\t", "z", "\n", "w"]
        assert result == expected

    def test_split_keep_ws_leading_whitespace(self, render):
        result = render._split_keep_ws("  hello")
        expected = ["", "  ", "hello"]
        assert result == expected

    def test_split_keep_ws_trailing_whitespace(self, render):
        result = render._split_keep_ws("hello  ")
        expected = ["hello", "  ", ""]
        assert result == expected

    def test_split_keep_ws_only_whitespace(self, render):
        result = render._split_keep_ws("   ")
        expected = ["", "   ", ""]
        assert result == expected

    def test_word_level_text_invalid_side(self, render):
        with pytest.raises(ValueError, match="side must be 'left' or 'right'"):
            render._word_level_text("a", "b", "invalid")

    def test_word_level_text_equal(self, render):
        left = "hello world"
        right = "hello world"
        result_left = render._word_level_text(left, right, "left")
        result_right = render._word_level_text(left, right, "right")
        assert result_left.plain == "hello world"
        assert result_right.plain == "hello world"
        assert len(result_left.spans) == 0
        assert len(result_right.spans) == 0

    def test_word_level_text_replace_left(self, render):
        left = "hello old"
        right = "hello new"
        result = render._word_level_text(left, right, "left")
        assert result.plain == "hello old"
        assert len(result.spans) == 1
        span = result.spans[0]
        assert span.start == 6
        assert span.end == 9
        assert span.style == "bold red"

    def test_word_level_text_replace_right(self, render):
        left = "hello old"
        right = "hello new"
        result = render._word_level_text(left, right, "right")
        assert result.plain == "hello new"
        assert len(result.spans) == 1
        span = result.spans[0]
        assert span.start == 6
        assert span.end == 9
        assert span.style == "bold green"

    def test_word_level_text_delete_left(self, render):
        left = "hello world extra"
        right = "hello world"
        result = render._word_level_text(left, right, "left")
        assert result.plain == "hello world extra"
        assert len(result.spans) == 2
        span1 = result.spans[0]
        assert span1.start == 11
        assert span1.end == 12
        assert span1.style == "bold red"
        span2 = result.spans[1]
        assert span2.start == 12
        assert span2.end == 17
        assert span2.style == "bold red"

    def test_word_level_text_delete_right_no_effect(self, render):
        left = "hello world extra"
        right = "hello world"
        result = render._word_level_text(left, right, "right")
        assert result.plain == "hello world"
        assert len(result.spans) == 0

    def test_word_level_text_insert_right(self, render):
        left = "hello world"
        right = "hello world extra"
        result = render._word_level_text(left, right, "right")
        assert result.plain == "hello world extra"
        assert len(result.spans) == 2
        span1 = result.spans[0]
        assert span1.start == 11
        assert span1.end == 12
        assert span1.style == "bold green"
        span2 = result.spans[1]
        assert span2.start == 12
        assert span2.end == 17
        assert span2.style == "bold green"

    def test_word_level_text_insert_left_no_effect(self, render):
        left = "hello world"
        right = "hello world extra"
        result = render._word_level_text(left, right, "left")
        assert result.plain == "hello world"
        assert len(result.spans) == 0

    def test_word_level_text_mixed_left(self, render):
        left = "the quick brown fox"
        right = "the fast brown dog"
        result = render._word_level_text(left, right, "left")
        assert result.plain == "the quick brown fox"
        assert len(result.spans) == 2
        span1 = result.spans[0]
        assert span1.start == 4
        assert span1.end == 9
        assert span1.style == "bold red"
        span2 = result.spans[1]
        assert span2.start == 16
        assert span2.end == 19
        assert span2.style == "bold red"

    def test_word_level_text_mixed_right(self, render):
        left = "the quick brown fox"
        right = "the fast brown dog"
        result = render._word_level_text(left, right, "right")
        assert result.plain == "the fast brown dog"
        assert len(result.spans) == 2
        span1 = result.spans[0]
        assert span1.start == 4
        assert span1.end == 8
        assert span1.style == "bold green"
        span2 = result.spans[1]
        assert span2.start == 15
        assert span2.end == 18
        assert span2.style == "bold green"

    @patch('alix.render.Console')
    def test_side_by_side_diff_equal_opcodes(self, mock_console, render):
        old = "line1\nline2\nline3"
        new = "line1\nline2\nline3"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 3
        for i in range(3):
            assert table.columns[0]._cells[i].plain == f"line{i+1}"
            assert table.columns[1]._cells[i].plain == f"line{i+1}"

    @patch('alix.render.Console')
    def test_side_by_side_diff_replace_opcodes(self, mock_console, render):
        old = "old line"
        new = "new line"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 1
        assert table.columns[0]._cells[0].plain == "old line"
        assert table.columns[1]._cells[0].plain == "new line"
        assert len(table.columns[0]._cells[0].spans) > 0
        assert any(span.style == "bold red" for span in table.columns[0]._cells[0].spans)
        assert len(table.columns[1]._cells[0].spans) > 0
        assert any(span.style == "bold green" for span in table.columns[1]._cells[0].spans)

    @patch('alix.render.Console')
    def test_side_by_side_diff_delete_opcodes(self, mock_console, render):
        old = "line1\nline2\nline3"
        new = "line1\nline3"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 3
        assert table.columns[0]._cells[0].plain == "line1"
        assert table.columns[1]._cells[0].plain == "line1"
        assert table.columns[0]._cells[1].plain == "line2"
        assert table.columns[0]._cells[1].style == "bold red"
        assert table.columns[1]._cells[1].plain == ""
        assert table.columns[0]._cells[2].plain == "line3"
        assert table.columns[1]._cells[2].plain == "line3"

    @patch('alix.render.Console')
    def test_side_by_side_diff_insert_opcodes(self, mock_console, render):
        old = "line1\nline3"
        new = "line1\nline2\nline3"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 3
        assert table.columns[0]._cells[0].plain == "line1"
        assert table.columns[1]._cells[0].plain == "line1"
        assert table.columns[0]._cells[1].plain == ""
        assert table.columns[1]._cells[1].plain == "line2"
        assert table.columns[1]._cells[1].style == "bold green"
        assert table.columns[0]._cells[2].plain == "line3"
        assert table.columns[1]._cells[2].plain == "line3"

    @patch('alix.render.Console')
    def test_side_by_side_diff_replace_unequal_lines(self, mock_console, render):
        old = "old1\nold2"
        new = "new1\nnew2\nnew3"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 3
        for i in range(2):
            assert table.columns[0]._cells[i].plain == f"old{i+1}"
            assert table.columns[1]._cells[i].plain == f"new{i+1}"
        assert table.columns[0]._cells[2].plain == ""
        assert table.columns[1]._cells[2].plain == "new3"
        assert len(table.columns[1]._cells[2].spans) == 1
        assert table.columns[1]._cells[2].spans[0].style == "bold green"

    @patch('alix.render.Console')
    def test_side_by_side_diff_empty_strings(self, mock_console, render):
        old = ""
        new = ""
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 0

    @patch('alix.render.Console')
    def test_side_by_side_diff_single_line_diff(self, mock_console, render):
        old = "old"
        new = "new"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 1
        assert table.columns[0]._cells[0].plain == "old"
        assert table.columns[1]._cells[0].plain == "new"

    @patch('alix.render.Console')
    def test_side_by_side_diff_multi_line_diff(self, mock_console, render):
        old = "line1\nline2\nline3\nline4"
        new = "line1\nnew2\nnew3\nline4"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 4
        assert table.columns[0]._cells[0].plain == "line1"
        assert table.columns[1]._cells[0].plain == "line1"
        assert table.columns[0]._cells[1].plain == "line2"
        assert table.columns[1]._cells[1].plain == "new2"
        assert table.columns[0]._cells[2].plain == "line3"
        assert table.columns[1]._cells[2].plain == "new3"
        assert table.columns[0]._cells[3].plain == "line4"
        assert table.columns[1]._cells[3].plain == "line4"

    @patch('alix.render.Console')
    def test_side_by_side_diff_replace_with_empty_lines(self, mock_console, render):
        old = "line1\nline2"
        new = "line1\nnew2\nnew3"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 3
        assert table.columns[0]._cells[0].plain == "line1"
        assert table.columns[1]._cells[0].plain == "line1"
        assert table.columns[0]._cells[1].plain == "line2"
        assert table.columns[1]._cells[1].plain == "new2"
        assert table.columns[0]._cells[2].plain == ""
        assert table.columns[1]._cells[2].plain == "new3"

    @patch('alix.render.SequenceMatcher')
    def test_side_by_side_diff_unknown_tag(self, mock_sm, render):
        mock_instance = MagicMock()
        mock_instance.get_opcodes.return_value = [("unknown", 0, 1, 0, 1)]
        mock_sm.return_value = mock_instance

        with pytest.raises(ValueError, match="Unknown tag: unknown"):
            render.side_by_side_diff("old", "new")
    def test_side_by_side_diff_invalid_input_types(self, render):
        with pytest.raises(AttributeError):
            render.side_by_side_diff(None, "new")
        with pytest.raises(AttributeError):
            render.side_by_side_diff("old", 123)
        with pytest.raises(AttributeError):
            render.side_by_side_diff([], "new")

    @patch('alix.render.Console')
    def test_side_by_side_diff_old_empty_new_content(self, mock_console, render):
        old = ""
        new = "content"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 1
        assert table.columns[0]._cells[0].plain == ""
        assert table.columns[1]._cells[0].plain == "content"
        assert table.columns[1]._cells[0].style == "bold green"

    @patch('alix.render.Console')
    def test_side_by_side_diff_old_content_new_empty(self, mock_console, render):
        old = "content"
        new = ""
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 1
        assert table.columns[0]._cells[0].plain == "content"
        assert table.columns[0]._cells[0].style == "bold red"
        assert table.columns[1]._cells[0].plain == ""

    @patch('alix.render.Console')
    def test_side_by_side_diff_with_empty_lines(self, mock_console, render):
        old = "line1\n\nline3"
        new = "line1\nline2\nline3"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 3
        assert table.columns[0]._cells[0].plain == "line1"
        assert table.columns[1]._cells[0].plain == "line1"
        assert table.columns[0]._cells[1].plain == ""
        assert table.columns[1]._cells[1].plain == "line2"
        assert table.columns[0]._cells[2].plain == "line3"
        assert table.columns[1]._cells[2].plain == "line3"

    @patch('alix.render.Console')
    def test_side_by_side_diff_unicode_characters(self, mock_console, render):
        old = "hello 🌍"
        new = "hello world"
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 1
        assert table.columns[0]._cells[0].plain == "hello 🌍"
        assert table.columns[1]._cells[0].plain == "hello world"
        assert len(table.columns[0]._cells[0].spans) > 0
        assert any(span.style == "bold red" for span in table.columns[0]._cells[0].spans)
        assert len(table.columns[1]._cells[0].spans) > 0
        assert any(span.style == "bold green" for span in table.columns[1]._cells[0].spans)

    @patch('alix.render.Console')
    def test_side_by_side_diff_very_long_lines(self, mock_console, render):
        long_old = "a" * 1000
        long_new = "b" * 1000
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(long_old, long_new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 1
        assert table.columns[0]._cells[0].plain == long_old
        assert table.columns[1]._cells[0].plain == long_new

    @patch('alix.render.Console')
    def test_side_by_side_diff_only_whitespace(self, mock_console, render):
        old = "   \n\t"
        new = "\n  "
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        render.side_by_side_diff(old, new)

        mock_console.assert_called_once()
        mock_console_instance.print.assert_called_once()
        table = mock_console_instance.print.call_args[0][0]
        assert isinstance(table, Table)
        assert len(table.rows) == 2
        assert table.columns[0]._cells[0].plain == "   "
        assert table.columns[1]._cells[0].plain == ""
        assert table.columns[0]._cells[1].plain == "\t"
        assert table.columns[1]._cells[1].plain == "  "

    def test_word_level_text_left_empty_right_content(self, render):
        result = render._word_level_text("", "hello", "left")
        assert result.plain == ""
        assert len(result.spans) == 0

    def test_word_level_text_left_content_right_empty(self, render):
        result = render._word_level_text("hello", "", "right")
        assert result.plain == ""
        assert len(result.spans) == 0

    def test_word_level_text_both_empty(self, render):
        result = render._word_level_text("", "", "left")
        assert result.plain == ""
        assert len(result.spans) == 0

    def test_word_level_text_no_whitespace_replace(self, render):
        left = "hello"
        right = "world"
        result_left = render._word_level_text(left, right, "left")
        assert result_left.plain == "hello"
        assert len(result_left.spans) == 1
        assert result_left.spans[0].style == "bold red"
        result_right = render._word_level_text(left, right, "right")
        assert result_right.plain == "world"
        assert len(result_right.spans) == 1
        assert result_right.spans[0].style == "bold green"

    def test_split_keep_ws_with_null_bytes(self, render):
        result = render._split_keep_ws("hello\x00world")
        expected = ["hello\x00world"]
        assert result == expected