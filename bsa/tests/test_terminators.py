"""
Unit tests for finalize_terminators functionality.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestFinalizeTerminators(unittest.TestCase):
    """Test the finalize_terminators method."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_if_statement_terminators(self):
        """Test that if statement blocks get correct terminators."""
        # Mock a set of blocks with if statement
        basic_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "IfStatement"
            },
            {
                "id": "Block1",  # True branch
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": None,
                "branch_type": "true"
            },
            {
                "id": "Block2",  # False branch
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": None,
                "branch_type": "false"
            },
            {
                "id": "Block3",  # Merge block
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": None
            }
        ]

        # Call finalize_terminators
        result = self.parser.finalize_terminators(basic_blocks)

        # Verify that the blocks have the right terminators
        self.assertEqual(result[0]["terminator"], "IfStatement")  # Already had a terminator
        self.assertEqual(result[1]["terminator"], "goto Block2")  # True branch should goto the next block
        self.assertEqual(result[2]["terminator"], "goto Block3")  # False branch should goto the next block
        self.assertEqual(result[3]["terminator"], "return")       # Last block should return

    def test_loop_terminators(self):
        """Test that loop blocks get correct terminators."""
        # Mock blocks with loop structure
        basic_blocks = [
            {
                "id": "Block0",               # Init block
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "goto Block1",  # Already has a terminator
                "is_loop_init": True
            },
            {
                "id": "Block1",               # Header block
                "statements": [{"type": "Expression", "node": {}}],
                "terminator": "if condition then goto Block2 else goto Block4",
                "is_loop_header": True
            },
            {
                "id": "Block2",               # Body block
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "goto Block3",
                "is_loop_body": True
            },
            {
                "id": "Block3",               # Increment block
                "statements": [{"type": "Expression", "node": {}}],
                "terminator": "goto Block1",  # Loop back edge
                "is_loop_increment": True
            },
            {
                "id": "Block4",               # Exit block
                "statements": [],
                "terminator": None,
                "is_loop_exit": True
            }
        ]

        # Call finalize_terminators
        result = self.parser.finalize_terminators(basic_blocks)

        # Verify that the blocks have the right terminators
        self.assertEqual(result[0]["terminator"], "goto Block1")  # Already had a terminator
        self.assertEqual(result[1]["terminator"], "if condition then goto Block2 else goto Block4")
        self.assertEqual(result[2]["terminator"], "goto Block3")
        self.assertEqual(result[3]["terminator"], "goto Block1")
        self.assertEqual(result[4]["terminator"], "return")       # Exit block should return

    def test_return_statement_terminators(self):
        """Test that blocks with Return statements get correct terminators."""
        # Mock blocks with return statement
        basic_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": None
            },
            {
                "id": "Block1",
                "statements": [{"type": "Return", "node": {}}],
                "terminator": "Return"  # Original terminator is just the type
            }
        ]

        # Call finalize_terminators
        result = self.parser.finalize_terminators(basic_blocks)

        # Verify that the blocks have the right terminators
        self.assertEqual(result[0]["terminator"], "goto Block1")  # Should goto next block
        self.assertEqual(result[1]["terminator"], "return")       # Return statement block

    def test_function_call_terminators(self):
        """Test that blocks with function calls get correct terminators."""
        # Mock blocks with function calls
        basic_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": None
            },
            {
                "id": "Block1",
                "statements": [{"type": "FunctionCall", "node": {}}],
                "terminator": None
            },
            {
                "id": "Block2",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": None
            }
        ]

        # Call finalize_terminators
        result = self.parser.finalize_terminators(basic_blocks)

        # Verify that the blocks have the right terminators
        self.assertEqual(result[0]["terminator"], "goto Block1")  # Should goto next block
        self.assertEqual(result[1]["terminator"], "goto Block2")  # Should goto next block
        self.assertEqual(result[2]["terminator"], "return")       # Last block should return

if __name__ == "__main__":
    unittest.main()