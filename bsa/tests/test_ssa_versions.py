"""
Unit tests for SSA variable versioning.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestSSAVersions(unittest.TestCase):
    """Test the SSA variable versioning functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_assign_ssa_versions(self):
        """Test assigning SSA versions to variables in basic blocks."""
        # Mock basic blocks for: function test() public { x = 1; if (x > 0) x = x + 1; }
        
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
                            "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                            "rightHandSide": {
                                "nodeType": "BinaryOperation",
                                "operator": "+",
                                "leftExpression": {"nodeType": "Identifier", "name": "x"},
                                "rightExpression": {"nodeType": "Literal", "value": "1"}
                            }
                        }
                    }
                ]
            }
        }
        
        # Mock the basic blocks with variable accesses
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
                "terminator": "if condition then goto Block1 else goto Block2",
                "accesses": {
                    "reads": ["x"],
                    "writes": ["x"]
                }
            },
            # Block1: x = x + 1; (true branch)
            {
                "id": "Block1",
                "statements": [
                    {
                        "type": "Assignment",
                        "node": {
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "Assignment",
                                "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                                "rightHandSide": {
                                    "nodeType": "BinaryOperation",
                                    "operator": "+",
                                    "leftExpression": {"nodeType": "Identifier", "name": "x"},
                                    "rightExpression": {"nodeType": "Literal", "value": "1"}
                                }
                            }
                        }
                    }
                ],
                "terminator": None,
                "branch_type": "true",
                "accesses": {
                    "reads": ["x"],
                    "writes": ["x"]
                }
            },
            # Block2: (false branch - empty)
            {
                "id": "Block2",
                "statements": [],
                "terminator": None,
                "branch_type": "false",
                "accesses": {
                    "reads": [],
                    "writes": []
                }
            }
        ]

        # Assign SSA versions
        ssa_blocks = self.parser.assign_ssa_versions(mock_basic_blocks)

        # Verify the results
        self.assertEqual(len(ssa_blocks), 3, "Should have three blocks")
        
        # Check Block0 SSA versions
        self.assertIn("ssa_versions", ssa_blocks[0], "Block0 should have ssa_versions field")
        self.assertEqual(ssa_blocks[0]["ssa_versions"]["writes"]["x"], 1, "Block0 should write to x_1")
        self.assertIn("ssa_statements", ssa_blocks[0], "Block0 should have ssa_statements field")
        
        # Print debugging information
        print("Block0 SSA versions:")
        print(ssa_blocks[0]["ssa_versions"])
        print("Block0 SSA statements:")
        for stmt in ssa_blocks[0]["ssa_statements"]:
            print(f"- {stmt}")
        
        self.assertTrue(any("x_1 =" in stmt for stmt in ssa_blocks[0]["ssa_statements"]), "Block0 should have statement with x_1")
        self.assertTrue(any("if (" in stmt and "x_1" in stmt for stmt in ssa_blocks[0]["ssa_statements"]), "Block0 should have if condition with x_1")
        
        # Check Block1 (true branch) SSA versions
        self.assertIn("ssa_versions", ssa_blocks[1], "Block1 should have ssa_versions field")
        self.assertEqual(ssa_blocks[1]["ssa_versions"]["reads"]["x"], 1, "Block1 should read x_1")
        self.assertEqual(ssa_blocks[1]["ssa_versions"]["writes"]["x"], 2, "Block1 should write to x_2")
        self.assertIn("ssa_statements", ssa_blocks[1], "Block1 should have ssa_statements field")
        self.assertTrue(any("x_2 =" in stmt and "x_1" in stmt for stmt in ssa_blocks[1]["ssa_statements"]), "Block1 should have statement with x_2 = ... x_1 ...")
        
        # Check Block2 (false branch) SSA versions
        self.assertIn("ssa_versions", ssa_blocks[2], "Block2 should have ssa_versions field")
        self.assertEqual(ssa_blocks[2]["ssa_versions"]["reads"], {}, "Block2 should have no reads")
        self.assertEqual(ssa_blocks[2]["ssa_versions"]["writes"], {}, "Block2 should have no writes")

if __name__ == "__main__":
    unittest.main()