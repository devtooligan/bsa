"""
Integration tests for block splitting through the entire SSA pipeline.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestBlockSplittingIntegration(unittest.TestCase):
    """Test the integration of improved block splitting throughout the SSA pipeline."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")
        
    def create_mock_function_mapping(self):
        """Create a simple function mapping for testing."""
        return {"testFunc": MagicMock()}
    
    def test_assignment_call_assignment_pipeline(self):
        """Test the full pipeline for a function with assignment, call, assignment."""
        # Create mock statements: x = 1; IA(a).hello(); y = 2;
        statements_typed = [
            {"type": "Assignment", "node": {
                "nodeType": "ExpressionStatement",
                "expression": {
                    "nodeType": "Assignment",
                    "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                    "rightHandSide": {"nodeType": "Literal", "value": "1"}
                }
            }},
            {"type": "FunctionCall", "node": {
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
            }},
            {"type": "Assignment", "node": {
                "nodeType": "ExpressionStatement",
                "expression": {
                    "nodeType": "Assignment",
                    "leftHandSide": {"nodeType": "Identifier", "name": "y"},
                    "rightHandSide": {"nodeType": "Literal", "value": "2"}
                }
            }}
        ]
        
        # Run through the pipeline
        blocks = self.parser.split_into_basic_blocks(statements_typed)
        refined_blocks = self.parser.refine_blocks_with_control_flow(blocks)
        blocks_with_accesses = self.parser.track_variable_accesses(refined_blocks)
        blocks_with_ssa = self.parser.assign_ssa_versions(blocks_with_accesses)
        blocks_with_calls = self.parser.classify_and_add_calls(blocks_with_ssa, self.create_mock_function_mapping())
        blocks_with_phi = self.parser.insert_phi_functions(blocks_with_calls)
        blocks_with_terminators = self.parser.finalize_terminators(blocks_with_phi)
        ssa_output = self.parser.integrate_ssa_output(blocks_with_terminators)
        
        # Verify the results
        self.assertEqual(len(blocks), 3)  # 3 basic blocks initially
        self.assertEqual(len(ssa_output), 3)  # 3 blocks in final SSA output
        
        # Check terminators
        self.assertEqual(ssa_output[0]["terminator"], "goto Block1")
        self.assertEqual(ssa_output[1]["terminator"], "goto Block2")
        self.assertEqual(ssa_output[2]["terminator"], "return")
    
    def test_if_call_assignment_pipeline(self):
        """Test the full pipeline for a function with if, call in true branch, assignment."""
        # Create mock statements for if (x > 0) IA(a).hello(); x = 1;
        statements_typed = [
            {"type": "IfStatement", "node": {
                "nodeType": "IfStatement",
                "condition": {
                    "nodeType": "BinaryOperation",
                    "operator": ">",
                    "leftExpression": {"nodeType": "Identifier", "name": "x"},
                    "rightExpression": {"nodeType": "Literal", "value": "0"}
                },
                "trueBody": {
                    "nodeType": "Block",
                    "statements": [{
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
                    }]
                },
                "falseBody": {}
            }},
            {"type": "Assignment", "node": {
                "nodeType": "ExpressionStatement",
                "expression": {
                    "nodeType": "Assignment",
                    "leftHandSide": {"nodeType": "Identifier", "name": "x"},
                    "rightHandSide": {"nodeType": "Literal", "value": "1"}
                }
            }}
        ]
        
        # Run through the pipeline
        blocks = self.parser.split_into_basic_blocks(statements_typed)
        refined_blocks = self.parser.refine_blocks_with_control_flow(blocks)
        blocks_with_accesses = self.parser.track_variable_accesses(refined_blocks)
        blocks_with_ssa = self.parser.assign_ssa_versions(blocks_with_accesses)
        blocks_with_calls = self.parser.classify_and_add_calls(blocks_with_ssa, self.create_mock_function_mapping())
        blocks_with_phi = self.parser.insert_phi_functions(blocks_with_calls)
        blocks_with_terminators = self.parser.finalize_terminators(blocks_with_phi)
        ssa_output = self.parser.integrate_ssa_output(blocks_with_terminators)
        
        # Verify the results - should be 4 blocks:
        # 1. If condition
        # 2. True branch with function call
        # 3. False branch (empty)
        # 4. Merge point with assignment
        self.assertEqual(len(blocks), 2)  # Original blocks
        self.assertGreaterEqual(len(refined_blocks), 4)  # At least 4 blocks after refinement
        self.assertGreaterEqual(len(ssa_output), 4)  # At least 4 blocks in SSA

if __name__ == '__main__':
    unittest.main()