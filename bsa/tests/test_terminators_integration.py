"""
Integration tests for control flow terminators.
"""

import unittest
import os
from unittest.mock import patch, mock_open
import json
from bsa.parser.ast_parser import ASTParser

class TestTerminatorsIntegration(unittest.TestCase):
    """Integration tests for the block terminators functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.parser = ASTParser("/dummy/path")
    
    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('glob.glob')
    def test_if_statement_integration(self, mock_glob, mock_exists, mock_open, mock_json_load):
        """Test that if statements get correct terminators in an integrated context."""
        # Mock a Solidity function with an if statement: x = 1; if (x > 0) x = 2;
        ast_data = {
            "ast": {
                "nodes": [{
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "nodes": [{
                        "nodeType": "FunctionDefinition",
                        "name": "testFunction", 
                        "visibility": "public",
                        "body": {
                            "statements": [
                                # x = 1;
                                {
                                    "nodeType": "ExpressionStatement",
                                    "expression": {
                                        "nodeType": "Assignment",
                                        "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                                        "rightHandSide": {"nodeType": "Literal", "value": "1"}
                                    }
                                },
                                # if (x > 0)
                                {
                                    "nodeType": "IfStatement",
                                    "condition": {
                                        "nodeType": "BinaryOperation",
                                        "leftExpression": {"nodeType": "Identifier", "name": "x"},
                                        "operator": ">",
                                        "rightExpression": {"nodeType": "Literal", "value": "0"}
                                    },
                                    "trueBody": {
                                        "nodeType": "Block",
                                        "statements": [
                                            # x = 2;
                                            {
                                                "nodeType": "ExpressionStatement",
                                                "expression": {
                                                    "nodeType": "Assignment",
                                                    "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                                                    "rightHandSide": {"nodeType": "Literal", "value": "2"}
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }]
                }]
            }
        }
        
        # Configure mocks
        mock_glob.return_value = ["fake_ast.json"]
        mock_exists.return_value = True
        mock_json_load.return_value = ast_data
        
        # Process AST
        contract_data = self.parser._process_ast(ast_data["ast"])
        
        # Verify contract data
        self.assertEqual(len(contract_data), 1)
        contract = contract_data[0]
        
        # Verify entrypoints
        self.assertEqual(len(contract["entrypoints"]), 1)
        entrypoint = contract["entrypoints"][0]
        
        # Verify blocks
        basic_blocks = entrypoint["basic_blocks"]
        self.assertGreater(len(basic_blocks), 2)  # Should have at least 3 blocks
        
        # Find the conditional block
        conditional_block = None
        for block in basic_blocks:
            if block.get("terminator", "").startswith("if "):
                conditional_block = block
                break
        
        # Verify conditional block exists and has correct terminator
        self.assertIsNotNone(conditional_block, "Conditional block not found")
        self.assertTrue("then goto " in conditional_block["terminator"])
        self.assertTrue("else goto " in conditional_block["terminator"])
        
        # Verify that all blocks have terminators
        for block in basic_blocks:
            self.assertIsNotNone(block.get("terminator"), f"Block {block.get('id')} has no terminator")
            
        # Verify that the last block has a return terminator
        last_block = basic_blocks[-1]
        self.assertEqual(last_block["terminator"], "return", "Last block should have return terminator")
    
    @patch('json.load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('glob.glob')
    def test_loop_integration(self, mock_glob, mock_exists, mock_open, mock_json_load):
        """Test that loops get correct terminators in an integrated context."""
        # Mock a Solidity function with a for loop: for (uint i = 0; i < 3; i++) x = i;
        ast_data = {
            "ast": {
                "nodes": [{
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "nodes": [{
                        "nodeType": "FunctionDefinition",
                        "name": "testFunction", 
                        "visibility": "public",
                        "body": {
                            "statements": [
                                # for (uint i = 0; i < 3; i++)
                                {
                                    "nodeType": "ForStatement",
                                    "initializationExpression": {
                                        "nodeType": "VariableDeclarationStatement",
                                        "declarations": [{
                                            "nodeType": "VariableDeclaration",
                                            "name": "i",
                                            "typeName": {"name": "uint"}
                                        }],
                                        "initialValue": {"nodeType": "Literal", "value": "0"}
                                    },
                                    "condition": {
                                        "nodeType": "BinaryOperation",
                                        "leftExpression": {"nodeType": "Identifier", "name": "i"},
                                        "operator": "<",
                                        "rightExpression": {"nodeType": "Literal", "value": "3"}
                                    },
                                    "loopExpression": {
                                        "nodeType": "ExpressionStatement",
                                        "expression": {
                                            "nodeType": "UnaryOperation",
                                            "operator": "++",
                                            "subExpression": {"nodeType": "Identifier", "name": "i"}
                                        }
                                    },
                                    "body": {
                                        "nodeType": "Block",
                                        "statements": [
                                            # x = i;
                                            {
                                                "nodeType": "ExpressionStatement",
                                                "expression": {
                                                    "nodeType": "Assignment",
                                                    "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                                                    "rightHandSide": {"nodeType": "Identifier", "name": "i"}
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }]
                }]
            }
        }
        
        # Configure mocks
        mock_glob.return_value = ["fake_ast.json"]
        mock_exists.return_value = True
        mock_json_load.return_value = ast_data
        
        # Process AST
        contract_data = self.parser._process_ast(ast_data["ast"])
        
        # Verify contract data
        self.assertEqual(len(contract_data), 1)
        contract = contract_data[0]
        
        # Verify entrypoints
        self.assertEqual(len(contract["entrypoints"]), 1)
        entrypoint = contract["entrypoints"][0]
        
        # Verify blocks
        basic_blocks = entrypoint["basic_blocks"]
        self.assertGreaterEqual(len(basic_blocks), 5)  # Should have at least 5 blocks for a for loop
        
        # Verify that all blocks have terminators
        for block in basic_blocks:
            self.assertIsNotNone(block.get("terminator"), f"Block {block.get('id')} has no terminator")
        
        # Find loop blocks
        init_block = None
        header_block = None
        body_block = None
        increment_block = None
        exit_block = None
        
        for block in basic_blocks:
            if block.get("is_loop_init"):
                init_block = block
            elif block.get("is_loop_header"):
                header_block = block
            elif block.get("is_loop_body"):
                body_block = block
            elif block.get("is_loop_increment"):
                increment_block = block
            elif block.get("is_loop_exit"):
                exit_block = block
        
        # Verify loop blocks exist
        self.assertIsNotNone(init_block, "Loop init block not found")
        self.assertIsNotNone(header_block, "Loop header block not found")
        self.assertIsNotNone(body_block, "Loop body block not found")
        self.assertIsNotNone(increment_block, "Loop increment block not found")
        self.assertIsNotNone(exit_block, "Loop exit block not found")
        
        # Verify loop structure
        self.assertTrue(init_block["terminator"].startswith("goto "))
        self.assertTrue("then goto " in header_block["terminator"])
        self.assertTrue("else goto " in header_block["terminator"])
        self.assertTrue(body_block["terminator"].startswith("goto "))
        self.assertTrue(increment_block["terminator"].startswith("goto "))
        self.assertTrue(exit_block["terminator"] in ["return", "goto Block"])

if __name__ == "__main__":
    unittest.main()