"""
Unit tests for control flow handling in basic blocks.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestControlFlow(unittest.TestCase):
    """Test the control flow handling in basic blocks."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_refine_blocks_with_control_flow(self):
        """Test refining basic blocks with control flow."""
        # Mock basic blocks for: function test() public { x = 1; if (x > 0) y = 2; z = 3; }
        
        # First, the if statement node
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
                            "rightHandSide": {"nodeType": "Literal", "value": "2"}
                        }
                    }
                ]
            }
        }
        
        # Mock basic blocks
        mock_basic_blocks = [
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
                "terminator": "IfStatement"
            },
            {
                "id": "Block1",
                "statements": [
                    {
                        "type": "Assignment",
                        "node": {
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "Assignment",
                                "leftHandSide": {"nodeType": "Identifier", "name": "z"},
                                "rightHandSide": {"nodeType": "Literal", "value": "3"}
                            }
                        }
                    }
                ],
                "terminator": None
            }
        ]

        # Refine blocks with control flow
        refined_blocks = self.parser.refine_blocks_with_control_flow(mock_basic_blocks)

        # Verify the results
        self.assertEqual(len(refined_blocks), 4, "Should have four refined blocks")
        
        # Check the conditional block
        self.assertEqual(refined_blocks[0]["id"], "Block0", "First block should be Block0")
        self.assertEqual(len(refined_blocks[0]["statements"]), 2, "Conditional block should have two statements")
        self.assertEqual(refined_blocks[0]["statements"][0]["type"], "Assignment", "First statement should be Assignment")
        self.assertEqual(refined_blocks[0]["statements"][1]["type"], "IfStatement", "Second statement should be IfStatement")
        self.assertTrue(refined_blocks[0]["terminator"].startswith("if"), "Terminator should start with 'if'")
        self.assertTrue("then goto" in refined_blocks[0]["terminator"], "Terminator should contain 'then goto'")
        self.assertTrue("else goto" in refined_blocks[0]["terminator"], "Terminator should contain 'else goto'")
        
        # Check the true branch block
        self.assertEqual(refined_blocks[1]["id"], "Block2", "True branch should be Block2")
        self.assertEqual(len(refined_blocks[1]["statements"]), 1, "True branch should have one statement")
        self.assertEqual(refined_blocks[1]["statements"][0]["type"], "Assignment", "Statement should be Assignment")
        self.assertEqual(refined_blocks[1]["branch_type"], "true", "Should be true branch")
        self.assertEqual(refined_blocks[1]["terminator"], "goto Block1", "Should jump to Block1")
        
        # Check the false branch block
        self.assertEqual(refined_blocks[2]["id"], "Block3", "False branch should be Block3")
        self.assertEqual(len(refined_blocks[2]["statements"]), 0, "False branch should be empty")
        self.assertEqual(refined_blocks[2]["branch_type"], "false", "Should be false branch")
        self.assertEqual(refined_blocks[2]["terminator"], "goto Block1", "Should jump to Block1")
        
        # Check the merge block
        self.assertEqual(refined_blocks[3]["id"], "Block1", "Merge block should be Block1")
        self.assertEqual(len(refined_blocks[3]["statements"]), 1, "Merge block should have one statement")
        self.assertEqual(refined_blocks[3]["statements"][0]["type"], "Assignment", "Statement should be Assignment")
        self.assertIsNone(refined_blocks[3]["terminator"], "Terminator should be None")

if __name__ == "__main__":
    unittest.main()