"""
Integration tests for inlining internal function calls in the full pipeline.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestInternalCallInliningIntegration(unittest.TestCase):
    """Test integration of internal function call inlining in the full pipeline."""

    def setUp(self):
        """Set up test environment with a temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.test_dir)

    def test_function_with_internal_call(self):
        """Test the end-to-end processing of a function with internal calls."""
        # Create a simple contract with an internal call
        parser = ASTParser("/dummy/path")
        
        # Create a basic state var 'x'
        state_var = {
            "name": "x",
            "type": "uint256",
            "location": [1, 1]
        }
        
        # Create internal function _setX that sets state var
        internal_func = {
            "name": "_setX",
            "location": [2, 1],
            "visibility": "internal",
            "body_raw": [],
            "calls": [],
            "basic_blocks": [
                {
                    "id": "Block0",
                    "statements": [{"type": "Assignment", "node": {}}],
                    "terminator": "return",
                    "accesses": {"reads": ["val"], "writes": ["x"]},
                    "ssa_versions": {"reads": {"val": 1}, "writes": {"x": 1}},
                    "ssa_statements": ["x_1 = val_1"]
                }
            ],
            "ssa": [
                {
                    "id": "Block0",
                    "ssa_statements": ["x_1 = val_1"],
                    "terminator": "return"
                }
            ]
        }
        
        # Create public function setValue that calls _setX
        public_func = {
            "name": "setValue",
            "location": [3, 1],
            "visibility": "public",
            "body_raw": [],
            "calls": [],
            "basic_blocks": [
                {
                    "id": "Block0",
                    "statements": [{"type": "FunctionCall", "node": {}}],
                    "terminator": "return",
                    "accesses": {"reads": ["val"], "writes": []},
                    "ssa_versions": {"reads": {"val": 1}, "writes": {}},
                    "ssa_statements": ["ret_1 = call[internal](_setX, val_1)"]
                }
            ],
            "ssa": [
                {
                    "id": "Block0",
                    "ssa_statements": ["ret_1 = call[internal](_setX, val_1)"],
                    "terminator": "return"
                }
            ]
        }
        
        # Mock contract data
        contract_data = {
            "contract": {
                "name": "TestContract",
                "state_vars": [state_var],
                "functions": {},
                "events": []
            },
            "entrypoints": [public_func]
        }
        
        # Add internal function to contract data
        all_funcs = [public_func, internal_func]
        
        # Create function map
        function_map = {"_setX": internal_func, "setValue": public_func}
        
        # Now perform inlining on the public function's blocks
        inlined_blocks = parser.inline_internal_calls(
            public_func["basic_blocks"], 
            function_map, 
            all_funcs
        )
        
        # Finalize block terminators after inlining
        blocks_with_terminators = parser.finalize_terminators(inlined_blocks)
        
        # Generate final SSA output with inlined calls
        ssa_output = parser.integrate_ssa_output(blocks_with_terminators)
        
        # Now check that inlining worked correctly
        self.assertEqual(len(ssa_output), 1, "Should have one block")
        
        # Verify that the inlined SSA includes the x assignment
        all_statements = []
        for block in ssa_output:
            all_statements.extend(block["ssa_statements"])
        
        # Look for both the call and the inlined effect
        has_call = any("call[internal](_setX" in stmt for stmt in all_statements)
        has_assignment = any("x_" in stmt and " = " in stmt for stmt in all_statements)
        
        self.assertTrue(has_call, "Should include the original call")
        self.assertTrue(has_assignment, "Should include inlined assignment to x")
        
        # Check that accesses were updated
        self.assertIn("x", inlined_blocks[0]["accesses"]["writes"], "Block should now write to x")

if __name__ == '__main__':
    unittest.main()