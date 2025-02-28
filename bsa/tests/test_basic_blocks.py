"""
Unit tests for basic block splitting.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestBasicBlocks(unittest.TestCase):
    """Test the basic block splitting functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_split_into_basic_blocks_simple(self):
        """Test splitting simple statements into basic blocks."""
        # Mock statements_typed for: function test() public { x = 1; foo(); return; }
        mock_statements_typed = [
            # x = 1;
            {
                "type": "Assignment",
                "node": {
                    "nodeType": "ExpressionStatement",
                    "expression": {
                        "nodeType": "Assignment",
                        "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                        "rightHandSide": {"nodeType": "Literal", "value": "1"}
                    }
                }
            },
            # foo();
            {
                "type": "FunctionCall",
                "node": {
                    "nodeType": "ExpressionStatement",
                    "expression": {
                        "nodeType": "FunctionCall",
                        "expression": {"nodeType": "Identifier", "name": "foo"}
                    }
                }
            },
            # return;
            {
                "type": "Return",
                "node": {
                    "nodeType": "Return"
                }
            }
        ]

        # Split into basic blocks
        basic_blocks = self.parser.split_into_basic_blocks(mock_statements_typed)

        # Verify the results - with the new logic, we should now have 3 blocks
        self.assertEqual(len(basic_blocks), 3, "Should have three basic blocks with the new splitting logic")
        
        # Check the first block
        self.assertEqual(basic_blocks[0]["id"], "Block0", "First block should be Block0")
        self.assertEqual(len(basic_blocks[0]["statements"]), 1, "First block should have one statement")
        self.assertEqual(basic_blocks[0]["statements"][0]["type"], "Assignment", "First statement should be Assignment")
        self.assertEqual(basic_blocks[0]["terminator"], "Assignment", "Block terminator should be Assignment")
        
        # Check the second block
        self.assertEqual(basic_blocks[1]["id"], "Block1", "Second block should be Block1")
        self.assertEqual(len(basic_blocks[1]["statements"]), 1, "Second block should have one statement")
        self.assertEqual(basic_blocks[1]["statements"][0]["type"], "FunctionCall", "Statement should be FunctionCall")
        self.assertEqual(basic_blocks[1]["terminator"], "FunctionCall", "Block terminator should be FunctionCall")
        
        # Check the third block
        self.assertEqual(basic_blocks[2]["id"], "Block2", "Third block should be Block2")
        self.assertEqual(len(basic_blocks[2]["statements"]), 1, "Third block should have one statement")
        self.assertEqual(basic_blocks[2]["statements"][0]["type"], "Return", "Statement should be Return")
        self.assertEqual(basic_blocks[2]["terminator"], "Return", "Block terminator should be Return")
        
    def test_split_into_basic_blocks_with_if(self):
        """Test splitting statements with if statement into basic blocks."""
        # Mock statements_typed for: function test() public { x = 1; if (x > 0) { foo(); } bar(); }
        mock_statements_typed = [
            # x = 1;
            {
                "type": "Assignment",
                "node": {
                    "nodeType": "ExpressionStatement",
                    "expression": {
                        "nodeType": "Assignment",
                        "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                        "rightHandSide": {"nodeType": "Literal", "value": "1"}
                    }
                }
            },
            # if (x > 0) { foo(); }
            {
                "type": "IfStatement",
                "node": {
                    "nodeType": "IfStatement",
                    "condition": {
                        "nodeType": "BinaryOperation",
                        "operator": ">",
                        "leftExpression": {"nodeType": "Identifier", "name": "x"},
                        "rightExpression": {"nodeType": "Literal", "value": "0"}
                    },
                    "trueBody": {
                        "nodeType": "Block",
                        "statements": [
                            {
                                "nodeType": "ExpressionStatement",
                                "expression": {
                                    "nodeType": "FunctionCall",
                                    "expression": {"nodeType": "Identifier", "name": "foo"}
                                }
                            }
                        ]
                    }
                }
            },
            # bar();
            {
                "type": "FunctionCall",
                "node": {
                    "nodeType": "ExpressionStatement",
                    "expression": {
                        "nodeType": "FunctionCall",
                        "expression": {"nodeType": "Identifier", "name": "bar"}
                    }
                }
            }
        ]

        # Split into basic blocks
        basic_blocks = self.parser.split_into_basic_blocks(mock_statements_typed)

        # Verify the results - with the new logic, we should now have 3 blocks
        self.assertEqual(len(basic_blocks), 3, "Should have three basic blocks with the new splitting logic")
        
        # Check the first block
        self.assertEqual(basic_blocks[0]["id"], "Block0", "First block should be Block0")
        self.assertEqual(len(basic_blocks[0]["statements"]), 1, "First block should have one statement")
        self.assertEqual(basic_blocks[0]["statements"][0]["type"], "Assignment", "First statement should be Assignment")
        self.assertEqual(basic_blocks[0]["terminator"], "Assignment", "Block terminator should be Assignment")
        
        # Check the second block
        self.assertEqual(basic_blocks[1]["id"], "Block1", "Second block should be Block1")
        self.assertEqual(len(basic_blocks[1]["statements"]), 1, "Second block should have one statement")
        self.assertEqual(basic_blocks[1]["statements"][0]["type"], "IfStatement", "Statement should be IfStatement")
        self.assertEqual(basic_blocks[1]["terminator"], "IfStatement", "Block terminator should be IfStatement")
        
        # Check the third block
        self.assertEqual(basic_blocks[2]["id"], "Block2", "Third block should be Block2")
        self.assertEqual(len(basic_blocks[2]["statements"]), 1, "Third block should have one statement")
        self.assertEqual(basic_blocks[2]["statements"][0]["type"], "FunctionCall", "Statement should be FunctionCall")
        self.assertIsNone(basic_blocks[2]["terminator"], "Block terminator should be None")

if __name__ == "__main__":
    unittest.main()