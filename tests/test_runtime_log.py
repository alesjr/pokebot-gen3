import io
import unittest

from modules.runtime_log import RuntimeLog


class TestRuntimeLog(unittest.TestCase):
    def test_captures_complete_lines_and_removes_ansi(self):
        log = RuntimeLog(io.StringIO(), max_lines=3)
        log.write("\x1b[31mShiny")
        log.write(" found\x1b[0m\nnext\n")
        self.assertEqual([item["text"] for item in log.snapshot()["lines"]], ["Shiny found", "next"])

    def test_is_bounded_and_supports_cursor(self):
        log = RuntimeLog(io.StringIO(), max_lines=2)
        log.write("one\ntwo\nthree\n")
        self.assertEqual([item["text"] for item in log.snapshot()["lines"]], ["two", "three"])
        self.assertEqual([item["text"] for item in log.snapshot(after=2)["lines"]], ["three"])


if __name__ == "__main__":
    unittest.main()
