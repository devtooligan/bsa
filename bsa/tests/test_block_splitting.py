"""
Tests for the improved block splitting functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestBlockSplitting(unittest.TestCase):
    """Test the improved block splitting functionality for functions with multiple statements."""

    def test_assignment_and_call_splitting(self):
        """Test that assignments and function calls create separate blocks."""
        # Create a parser and mock the input
        parser = ASTParser("/dummy/path")
        
        # Mock statements: x = 1; IA(a).hello(); y = 2;
        statements_typed = [
            {"type": "Assignment", "node": {"nodeType": "ExpressionStatement"}},
            {"type": "FunctionCall", "node": {"nodeType": "ExpressionStatement"}},
            {"type": "Assignment", "node": {"nodeType": "ExpressionStatement"}}
        ]
        
        # Call the function
        blocks = parser.split_into_basic_blocks(statements_typed)
        
        # Verify that we get 3 blocks
        self.assertEqual(len(blocks), 3)
        
        # Verify block contents
        self.assertEqual(blocks[0]["id"], "Block0")
        self.assertEqual(len(blocks[0]["statements"]), 1)
        self.assertEqual(blocks[0]["statements"][0]["type"], "Assignment")
        
        self.assertEqual(blocks[1]["id"], "Block1")
        self.assertEqual(len(blocks[1]["statements"]), 1)
        self.assertEqual(blocks[1]["statements"][0]["type"], "FunctionCall")
        
        self.assertEqual(blocks[2]["id"], "Block2")
        self.assertEqual(len(blocks[2]["statements"]), 1)
        self.assertEqual(blocks[2]["statements"][0]["type"], "Assignment")

    def test_if_with_call_splitting(self):
        """Test that if statements with function calls create separate blocks."""
        # Create a parser and mock the input
        parser = ASTParser("/dummy/path")
        
        # Mock statements: if (x > 0) IA(a).hello(); x = 1;
        statements_typed = [
            {"type": "IfStatement", "node": {"nodeType": "IfStatement"}},
            {"type": "Assignment", "node": {"nodeType": "ExpressionStatement"}}
        ]
        
        # Call the function
        blocks = parser.split_into_basic_blocks(statements_typed)
        
        # Verify that we get 2 blocks
        self.assertEqual(len(blocks), 2)
        
        # Verify block contents
        self.assertEqual(blocks[0]["id"], "Block0")
        self.assertEqual(len(blocks[0]["statements"]), 1)
        self.assertEqual(blocks[0]["statements"][0]["type"], "IfStatement")
        
        self.assertEqual(blocks[1]["id"], "Block1")
        self.assertEqual(len(blocks[1]["statements"]), 1)
        self.assertEqual(blocks[1]["statements"][0]["type"], "Assignment")

    def test_for_loop_with_call_splitting(self):
        """Test that for loops with function calls create separate blocks."""
        # Create a parser and mock the input
        parser = ASTParser("/dummy/path")
        
        # Mock statements: for (uint i = 0; i < 2; i++) IA(a).hello();
        statements_typed = [
            {"type": "ForLoop", "node": {"nodeType": "ForStatement"}}
        ]
        
        # Call the function
        blocks = parser.split_into_basic_blocks(statements_typed)
        
        # Verify that we get 1 block (the splitting of the for loop is handled by refine_blocks_with_control_flow)
        self.assertEqual(len(blocks), 1)
        
        # Verify block contents
        self.assertEqual(blocks[0]["id"], "Block0")
        self.assertEqual(len(blocks[0]["statements"]), 1)
        self.assertEqual(blocks[0]["statements"][0]["type"], "ForLoop")

    def test_assignment_and_return_splitting(self):
        """Test that assignments followed by returns create separate blocks."""
        # Create a parser and mock the input
        parser = ASTParser("/dummy/path")
        
        # Mock statements: x = 1; return;
        statements_typed = [
            {"type": "Assignment", "node": {"nodeType": "ExpressionStatement"}},
            {"type": "Return", "node": {"nodeType": "Return"}}
        ]
        
        # Call the function
        blocks = parser.split_into_basic_blocks(statements_typed)
        
        # Verify that we get 2 blocks
        self.assertEqual(len(blocks), 2)
        
        # Verify block contents
        self.assertEqual(blocks[0]["id"], "Block0")
        self.assertEqual(len(blocks[0]["statements"]), 1)
        self.assertEqual(blocks[0]["statements"][0]["type"], "Assignment")
        
        self.assertEqual(blocks[1]["id"], "Block1")
        self.assertEqual(len(blocks[1]["statements"]), 1)
        self.assertEqual(blocks[1]["statements"][0]["type"], "Return")

if __name__ == '__main__':
    unittest.main()