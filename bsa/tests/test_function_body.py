import unittest
from unittest.mock import patch, mock_open
import json
from bsa.parser.ast_parser import ASTParser
from bsa.parser.nodes import ASTNode

class TestFunctionBodyExtraction(unittest.TestCase):
    def test_extract_function_body(self):
        """Test that the function body extraction correctly extracts statements."""
        # Create a mock AST parser
        parser = ASTParser("/mock/path")
        
        # Create a mock function definition node with a simple statement
        function_def = {
            "nodeType": "FunctionDefinition",
            "name": "test",
            "visibility": "public",
            "body": {
                "nodeType": "Block",
                "statements": [
                    {
                        "nodeType": "ExpressionStatement",
                        "expression": {
                            "nodeType": "Assignment",
                            "leftHandSide": {
                                "nodeType": "Identifier",
                                "name": "x"
                            },
                            "rightHandSide": {
                                "nodeType": "Literal",
                                "value": "1"
                            }
                        }
                    }
                ]
            }
        }
        
        # Extract raw statements
        statements = parser.extract_function_body(function_def)
        
        # Verify the statements list contains the expected statement
        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0]["nodeType"], "ExpressionStatement")
        self.assertEqual(statements[0]["expression"]["nodeType"], "Assignment")
        self.assertEqual(statements[0]["expression"]["leftHandSide"]["name"], "x")
        self.assertEqual(statements[0]["expression"]["rightHandSide"]["value"], "1")
    
    def test_extract_function_body_empty(self):
        """Test that the function body extraction handles empty bodies correctly."""
        # Create a mock AST parser
        parser = ASTParser("/mock/path")
        
        # Create a mock function definition node with an empty body
        function_def = {
            "nodeType": "FunctionDefinition",
            "name": "emptyFunction",
            "visibility": "public",
            "body": {
                "nodeType": "Block",
                "statements": []
            }
        }
        
        # Extract raw statements
        statements = parser.extract_function_body(function_def)
        
        # Verify the statements list is empty
        self.assertEqual(len(statements), 0)
    
    def test_extract_function_body_no_body(self):
        """Test that the function body extraction handles missing body correctly."""
        # Create a mock AST parser
        parser = ASTParser("/mock/path")
        
        # Create a mock function definition node with no body
        function_def = {
            "nodeType": "FunctionDefinition",
            "name": "noBodyFunction",
            "visibility": "public"
        }
        
        # Extract raw statements
        statements = parser.extract_function_body(function_def)
        
        # Verify the statements list is empty
        self.assertEqual(len(statements), 0)
    
    @patch('json.load')
    @patch('builtins.open')
    @patch('glob.glob')
    @patch('subprocess.run')
    def test_process_contract_with_function_body_raw(self, mock_run, mock_glob, mock_open_func, mock_json_load):
        """Test that the processed contract data includes body_raw for entrypoints."""
        # Create a mock AST parser
        parser = ASTParser("/mock/path")
        
        # Mock the source file content
        src_content = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Test {
    uint x;
    
    function test() public {
        x = 1;
    }
}"""
        
        # Create a mock AST with a function containing a statement
        ast_data = {
            "ast": {
                "nodeType": "SourceUnit",
                "nodes": [
                    {
                        "nodeType": "PragmaDirective",
                        "literals": ["solidity", "^", "0.8", ".0"]
                    },
                    {
                        "nodeType": "ContractDefinition",
                        "name": "Test",
                        "nodes": [
                            {
                                "nodeType": "VariableDeclaration",
                                "name": "x",
                                "stateVariable": True,
                                "typeName": {"name": "uint"},
                                "src": "50:6:0"
                            },
                            {
                                "nodeType": "FunctionDefinition",
                                "name": "test",
                                "visibility": "public",
                                "src": "70:30:0",
                                "body": {
                                    "nodeType": "Block",
                                    "statements": [
                                        {
                                            "nodeType": "ExpressionStatement",
                                            "expression": {
                                                "nodeType": "Assignment",
                                                "leftHandSide": {
                                                    "nodeType": "Identifier",
                                                    "name": "x"
                                                },
                                                "rightHandSide": {
                                                    "nodeType": "Literal",
                                                    "value": "1"
                                                }
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        # Set parser's source text
        parser.source_text = src_content
        
        # Process the AST
        contract_data = parser._process_ast(ast_data["ast"])
        
        # Verify contract data contains an entrypoint with body_raw
        self.assertTrue(contract_data)
        self.assertEqual(len(contract_data), 1)
        entrypoints = contract_data[0]["entrypoints"]
        self.assertEqual(len(entrypoints), 1)
        
        # Check that the entrypoint has body_raw
        entrypoint = entrypoints[0]
        self.assertEqual(entrypoint["name"], "test")
        self.assertIn("body_raw", entrypoint)
        
        # Verify body_raw contains the expected statement
        body_raw = entrypoint["body_raw"]
        self.assertEqual(len(body_raw), 1)
        self.assertEqual(body_raw[0]["nodeType"], "ExpressionStatement")
        
        # Check that the statement is an assignment to x = 1
        expression = body_raw[0]["expression"]
        self.assertEqual(expression["nodeType"], "Assignment")
        self.assertEqual(expression["leftHandSide"]["name"], "x")
        self.assertEqual(expression["rightHandSide"]["value"], "1")

if __name__ == '__main__':
    unittest.main()