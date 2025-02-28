"""
Unit tests for statement classifier.
"""

import unittest
from bsa.parser.ast_parser import ASTParser

class TestStatementClassifier(unittest.TestCase):
    """Test the statement classifier functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")  # Path doesn't matter for unit test

    def test_classify_statements(self):
        """Test classifying statements from a Solidity function body."""
        # Mock AST nodes for: x = 1; foo(); if (x > 0) return;
        mock_body_raw = [
            # x = 1;
            {
                "nodeType": "ExpressionStatement",
                "expression": {
                    "nodeType": "Assignment",
                    "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                    "rightHandSide": {"nodeType": "Literal", "value": "1"}
                }
            },
            # foo();
            {
                "nodeType": "ExpressionStatement",
                "expression": {
                    "nodeType": "FunctionCall",
                    "expression": {"nodeType": "Identifier", "name": "foo"}
                }
            },
            # if (x > 0) return;
            {
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
                        {"nodeType": "Return"}
                    ]
                }
            }
        ]

        # Classify the statements
        statements_typed = self.parser.classify_statements(mock_body_raw)

        # Verify the results
        self.assertEqual(len(statements_typed), 3, "Should have three typed statements")
        
        # Check each statement type
        self.assertEqual(statements_typed[0]["type"], "Assignment", "First statement should be Assignment")
        self.assertEqual(statements_typed[1]["type"], "FunctionCall", "Second statement should be FunctionCall")
        self.assertEqual(statements_typed[2]["type"], "IfStatement", "Third statement should be IfStatement")
        
        # Verify the nodes are preserved
        self.assertEqual(statements_typed[0]["node"], mock_body_raw[0], "Node should be preserved")
        self.assertEqual(statements_typed[1]["node"], mock_body_raw[1], "Node should be preserved")
        self.assertEqual(statements_typed[2]["node"], mock_body_raw[2], "Node should be preserved")

if __name__ == "__main__":
    unittest.main()