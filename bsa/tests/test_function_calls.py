"""
Unit tests for function call classification.
"""

import unittest
from bsa.parser.ast_parser import ASTParser
from bsa.parser.nodes import ASTNode

class TestFunctionCalls(unittest.TestCase):
    """Test the function call classification functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_classify_and_add_calls(self):
        """Test classifying and adding function calls to SSA statements."""
        # Create a function map with internal functions
        function_map = {
            "foo": ASTNode({"name": "foo", "nodeType": "FunctionDefinition"})
        }
        
        # Create a block with function calls: x = 1; foo(x); other.bar(x);
        mock_basic_blocks = [
            {
                "id": "Block0",
                "statements": [
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
                    # foo(x);
                    {
                        "type": "FunctionCall",
                        "node": {
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "FunctionCall",
                                "expression": {"nodeType": "Identifier", "name": "foo"},
                                "arguments": [{"nodeType": "Identifier", "name": "x"}]
                            }
                        }
                    },
                    # other.bar(x);
                    {
                        "type": "FunctionCall",
                        "node": {
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "FunctionCall",
                                "expression": {
                                    "nodeType": "MemberAccess",
                                    "expression": {"nodeType": "Identifier", "name": "other"},
                                    "memberName": "bar"
                                },
                                "arguments": [{"nodeType": "Identifier", "name": "x"}]
                            }
                        }
                    }
                ],
                "terminator": None,
                "accesses": {
                    "reads": ["x"],
                    "writes": ["x"]
                },
                "ssa_versions": {
                    "reads": {"x": 1},
                    "writes": {"x": 1}
                },
                "ssa_statements": [
                    "x_1 = ",
                    "call(x_1 )",
                    "call(x_1 )"
                ]
            }
        ]

        # Classify and add function calls
        classified_blocks = self.parser.classify_and_add_calls(mock_basic_blocks, function_map)

        # Verify the results
        self.assertEqual(len(classified_blocks), 1, "Should have one block")
        
        # Check the SSA statements
        self.assertEqual(len(classified_blocks[0]["ssa_statements"]), 3, "Should have three statements")
        
        # Check the first statement (assignment) - should be unchanged
        self.assertEqual(classified_blocks[0]["ssa_statements"][0], "x_1 = ", "First statement should be assignment")
        
        # Check the second statement (internal call)
        self.assertTrue("call[internal]" in classified_blocks[0]["ssa_statements"][1], 
                       "Second statement should be internal call")
        self.assertTrue("foo" in classified_blocks[0]["ssa_statements"][1], 
                       "Second statement should reference foo function")
        self.assertTrue("x_1" in classified_blocks[0]["ssa_statements"][1], 
                       "Internal call should include argument x_1")
        
        # Check the third statement (external call)
        self.assertTrue("call[external]" in classified_blocks[0]["ssa_statements"][2], 
                       "Third statement should be external call")
        self.assertTrue("bar" in classified_blocks[0]["ssa_statements"][2], 
                       "Third statement should reference bar function")
        self.assertTrue("x_1" in classified_blocks[0]["ssa_statements"][2], 
                       "External call should include argument x_1")

if __name__ == "__main__":
    unittest.main()