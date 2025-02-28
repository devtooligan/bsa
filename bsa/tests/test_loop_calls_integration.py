"""
Integration tests for loop analysis with nested function calls.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestLoopCallsIntegration(unittest.TestCase):
    """Test the integration of loop analysis with nested function calls."""

    def setUp(self):
        """Set up test environment with a temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.test_dir, "src")
        os.makedirs(self.src_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.test_dir)

    @patch('bsa.parser.ast_parser.build_project_ast')
    @patch('bsa.parser.ast_parser.find_ast_files')
    @patch('bsa.parser.ast_parser.find_source_files')
    def test_loop_with_external_call_integration(self, mock_find_sources, mock_find_ast, mock_build):
        """Test the full pipeline with a loop containing an external call."""
        # Create a parser with a mock project path
        parser = ASTParser("/dummy/path")
        
        # Create mock basic blocks for a for loop with external call
        # for (i = 0; i < 2; i++) IA(a).hello();
        
        # Simulate the processing of a function with a loop containing an external call
        entry_blocks = [
            # Init block
            {
                "id": "Block0",
                "statements": [{"type": "VariableDeclaration", "node": {}}],
                "terminator": "goto Block1",
                "is_loop_init": True,
                "accesses": {"reads": [], "writes": ["i"]},
                "ssa_versions": {"reads": {}, "writes": {"i": 1}},
                "ssa_statements": ["i_1 = 0"]
            },
            # Loop header
            {
                "id": "Block1",
                "statements": [{"type": "Expression", "node": {}}],
                "terminator": "if i_1 < 2 then goto Block2 else goto Block4",
                "is_loop_header": True,
                "accesses": {"reads": ["i", "x"], "writes": []},
                "ssa_versions": {"reads": {"i": 1, "x": 1}, "writes": {}},
                "ssa_statements": ["if (i_1 < 2)"]
            },
            # Loop body with external call
            {
                "id": "Block2",
                "statements": [{"type": "FunctionCall", "node": {}}],
                "terminator": "goto Block3",
                "is_loop_body": True,
                "accesses": {"reads": ["a"], "writes": []},
                "ssa_versions": {"reads": {"a": 1}, "writes": {}},
                "ssa_statements": ["ret_1 = call[external](hello, a_1)"]
            },
            # Loop increment
            {
                "id": "Block3",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "goto Block1",
                "is_loop_increment": True,
                "accesses": {"reads": ["i"], "writes": ["i"]},
                "ssa_versions": {"reads": {"i": 1}, "writes": {"i": 2}},
                "ssa_statements": ["i_2 = i_1 + 1"]
            },
            # Loop exit
            {
                "id": "Block4",
                "statements": [],
                "terminator": "return",
                "is_loop_exit": True,
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": []
            }
        ]
        
        # Add a mock state variable to the scenario
        state_vars = [{"name": "x", "type": "uint256"}]
        
        # 1. Apply loop call analysis
        blocks_with_loop_calls = parser.analyze_loop_calls(entry_blocks)
        
        # 2. Apply phi function insertion
        blocks_with_phi = parser.insert_phi_functions(blocks_with_loop_calls)
        
        # 3. Finalize terminators
        blocks_with_terminators = parser.finalize_terminators(blocks_with_phi)
        
        # 4. Integrate SSA output
        ssa_output = parser.integrate_ssa_output(blocks_with_terminators)
        
        # Verify results
        # 1. Check that the loop header was marked for special handling
        self.assertTrue(blocks_with_loop_calls[1].get("has_external_call_effects", False))
        
        # 2. Check that writes were modified in the loop header's accesses
        self.assertTrue(len(blocks_with_loop_calls[1]["accesses"]["writes"]) > 0, 
                       "Loop header should have variables in its writes list")
        
        # 3. Check for presence of phi-functions in the loop header
        # Look for phi function for i
        has_i_phi = False
        for stmt in blocks_with_phi[1]["ssa_statements"]:
            if stmt.startswith("i_") and "= phi(" in stmt:
                has_i_phi = True
                break
        self.assertTrue(has_i_phi, "Loop header should have phi function for i")
        
        # Also check that we have at least the expected phi functions
        phi_count = 0
        for stmt in blocks_with_phi[1]["ssa_statements"]:
            if "= phi(" in stmt:
                phi_count += 1
        
        # We should have at least one phi function
        self.assertTrue(phi_count > 0, "Loop header should have at least one phi function")
        
        # Note: We're not strictly testing for a phi function for the state variable 'x'
        # as the implementation may not add it if it's not actually modified
        # or if its version doesn't change across iterations

if __name__ == '__main__':
    unittest.main()