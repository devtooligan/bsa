"""
Unit tests for external call classification.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestExternalCall(unittest.TestCase):
    """Test the classification of IA(a).hello() style external calls."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_contract_cast_external_call(self):
        """Test classifying calls that use contract type casting like IA(a).hello()."""
        # Create a function map with internal functions
        function_map = {}
        
        # Create a block with a contract cast external call: IA(a).hello();
        mock_basic_blocks = [
            {
                "id": "Block0",
                "statements": [
                    # IA(a).hello();
                    {
                        "type": "FunctionCall",
                        "node": {
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "FunctionCall",
                                "expression": {
                                    "nodeType": "MemberAccess",
                                    "memberName": "hello",
                                    "expression": {
                                        "nodeType": "FunctionCall",
                                        "expression": {"nodeType": "Identifier", "name": "IA"},
                                        "arguments": [{"nodeType": "Identifier", "name": "a"}]
                                    }
                                },
                                "arguments": []
                            }
                        }
                    }
                ],
                "terminator": None,
                "accesses": {
                    "reads": ["a"],
                    "writes": []
                },
                "ssa_versions": {
                    "reads": {"a": 1},
                    "writes": {}
                },
                "ssa_statements": [
                    "call(a_1 )"
                ]
            }
        ]

        # Classify and add function calls
        classified_blocks = self.parser.classify_and_add_calls(mock_basic_blocks, function_map)

        # Verify the results
        self.assertEqual(len(classified_blocks), 1, "Should have one block")
        
        # Check the SSA statements
        self.assertEqual(len(classified_blocks[0]["ssa_statements"]), 1, "Should have one statement")
        
        # Check the statement (should be classified as external)
        self.assertTrue("call[external]" in classified_blocks[0]["ssa_statements"][0], 
                       "Statement should be classified as external call")
        self.assertTrue("hello" in classified_blocks[0]["ssa_statements"][0], 
                       "Statement should reference hello function")

if __name__ == "__main__":
    unittest.main()