"""
Unit tests for variable access tracking.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestVariableAccesses(unittest.TestCase):
    """Test the variable access tracking functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_track_variable_accesses(self):
        """Test tracking variable reads and writes across blocks."""
        # Mock basic blocks for: function test() public { x = 1; if (x > 0) y = x; }
        
        # First create the if statement node
        if_node = {
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
                            "nodeType": "Assignment",
                            "leftHandSide": {"nodeType": "Identifier", "name": "y"},
                            "rightHandSide": {"nodeType": "Identifier", "name": "x"}
                        }
                    }
                ]
            }
        }
        
        # Mock the basic blocks
        mock_basic_blocks = [
            # Block0: x = 1; if (x > 0)
            {
                "id": "Block0",
                "statements": [
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
                    {
                        "type": "IfStatement",
                        "node": if_node
                    }
                ],
                "terminator": "if condition then goto Block1 else goto Block2"
            },
            # Block1: y = x; (true branch)
            {
                "id": "Block1",
                "statements": [
                    {
                        "type": "Assignment",
                        "node": {
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "Assignment",
                                "leftHandSide": {"nodeType": "Identifier", "name": "y"},
                                "rightHandSide": {"nodeType": "Identifier", "name": "x"}
                            }
                        }
                    }
                ],
                "terminator": None,
                "branch_type": "true"
            },
            # Block2: (false branch - empty)
            {
                "id": "Block2",
                "statements": [],
                "terminator": None,
                "branch_type": "false"
            }
        ]

        # Track variable accesses
        tracked_blocks = self.parser.track_variable_accesses(mock_basic_blocks)

        # Verify the results
        self.assertEqual(len(tracked_blocks), 3, "Should have three blocks")
        
        # Check Block0 accesses
        self.assertIn("accesses", tracked_blocks[0], "Block0 should have accesses field")
        self.assertEqual(tracked_blocks[0]["accesses"]["writes"], ["x"], "Block0 should write to x")
        self.assertEqual(tracked_blocks[0]["accesses"]["reads"], ["x"], "Block0 should read x in the if condition")
        
        # Check Block1 (true branch) accesses
        self.assertIn("accesses", tracked_blocks[1], "Block1 should have accesses field")
        self.assertEqual(tracked_blocks[1]["accesses"]["writes"], ["y"], "Block1 should write to y")
        self.assertEqual(tracked_blocks[1]["accesses"]["reads"], ["x"], "Block1 should read x in the assignment")
        
        # Check Block2 (false branch) accesses
        self.assertIn("accesses", tracked_blocks[2], "Block2 should have accesses field")
        self.assertEqual(tracked_blocks[2]["accesses"]["writes"], [], "Block2 should have no writes")
        self.assertEqual(tracked_blocks[2]["accesses"]["reads"], [], "Block2 should have no reads")

if __name__ == "__main__":
    unittest.main()