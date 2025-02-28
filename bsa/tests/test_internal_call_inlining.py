"""
Tests for inlining internal function calls in SSA.
"""

import unittest
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestInternalCallInlining(unittest.TestCase):
    """Test inlining of internal function calls in SSA."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")
        
    def test_inline_simple_call(self):
        """Test inlining a simple internal function call."""
        # Create mock blocks for caller: foo() { bar(); }
        caller_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "FunctionCall", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": ["ret_1 = call[internal](bar)"]
            }
        ]
        
        # Create mock blocks for callee: bar() { x = 1; }
        callee_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": [], "writes": ["x"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = 1"]
            }
        ]
        
        # Mock function map and entrypoints data
        function_map = {"bar": MagicMock()}
        entrypoints_data = [
            {
                "name": "foo",
                "basic_blocks": caller_blocks,
                "ssa": caller_blocks
            },
            {
                "name": "bar",
                "basic_blocks": callee_blocks,
                "ssa": callee_blocks
            }
        ]
        
        # Call the function
        result_blocks = self.parser.inline_internal_calls(caller_blocks, function_map, entrypoints_data)
        
        # Verify the results
        self.assertEqual(len(result_blocks), 1, "Should have one block")
        
        # Check the SSA statements in the result
        ssa_statements = result_blocks[0]["ssa_statements"]
        self.assertEqual(len(ssa_statements), 2, "Should have 2 statements (inlined + original call)")
        
        # The inlined statement should be present
        has_inlined_stmt = any("x_" in stmt and "= 1" in stmt for stmt in ssa_statements)
        self.assertTrue(has_inlined_stmt, "Should have inlined x = 1 assignment")
        
        # The original call should still be present
        has_call_stmt = any("call[internal](bar)" in stmt for stmt in ssa_statements)
        self.assertTrue(has_call_stmt, "Should preserve the original call")
        
        # Check that accesses were updated properly by the implementation
        self.assertIn("x", result_blocks[0]["accesses"]["writes"], "x should be in writes list")
    
    def test_inline_with_loop(self):
        """Test inlining with a loop that contains an internal call."""
        # Create mock blocks for a loop with internal call: while (i < 2) { bar(); i++; }
        caller_blocks = [
            {
                "id": "Block0",  # Pre-loop block
                "statements": [{"type": "VariableDeclaration", "node": {}}],
                "terminator": "goto Block1",
                "accesses": {"reads": [], "writes": ["i"]},
                "ssa_versions": {"reads": {}, "writes": {"i": 1}},
                "ssa_statements": ["i_1 = 0"]
            },
            {
                "id": "Block1",  # Loop header
                "statements": [{"type": "Expression", "node": {}}],
                "terminator": "if i_1 < 2 then goto Block2 else goto Block4",
                "is_loop_header": True,
                "accesses": {"reads": ["i"], "writes": []},
                "ssa_versions": {"reads": {"i": 1}, "writes": {}},
                "ssa_statements": ["if (i_1 < 2)"]
            },
            {
                "id": "Block2",  # Loop body with call
                "statements": [{"type": "FunctionCall", "node": {}}],
                "terminator": "goto Block3",
                "is_loop_body": True,
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": ["ret_1 = call[internal](bar)"]
            },
            {
                "id": "Block3",  # Loop increment
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "goto Block1",
                "is_loop_increment": True,
                "accesses": {"reads": ["i"], "writes": ["i"]},
                "ssa_versions": {"reads": {"i": 1}, "writes": {"i": 2}},
                "ssa_statements": ["i_2 = i_1 + 1"]
            },
            {
                "id": "Block4",  # Loop exit
                "statements": [],
                "terminator": "return",
                "is_loop_exit": True,
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": []
            }
        ]
        
        # Create mock blocks for callee: bar() { x = 1; }
        callee_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": [], "writes": ["x"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = 1"]
            }
        ]
        
        # Mock function map and entrypoints data
        function_map = {"bar": MagicMock()}
        entrypoints_data = [
            {
                "name": "foo",
                "basic_blocks": caller_blocks,
                "ssa": caller_blocks
            },
            {
                "name": "bar",
                "basic_blocks": callee_blocks,
                "ssa": callee_blocks
            }
        ]
        
        # Call the function
        result_blocks = self.parser.inline_internal_calls(caller_blocks, function_map, entrypoints_data)
        
        # Verify the results
        self.assertEqual(len(result_blocks), 5, "Should still have 5 blocks")
        
        # Check that the call block has inlined statements
        call_block = result_blocks[2]  # Block2 with the call
        ssa_statements = call_block["ssa_statements"]
        self.assertEqual(len(ssa_statements), 2, "Should have 2 statements in call block")
        
        # The inlined statement should be present
        has_inlined_stmt = any("x_" in stmt and "= 1" in stmt for stmt in ssa_statements)
        self.assertTrue(has_inlined_stmt, "Should have inlined x = 1 assignment")
        
        # Check that accesses were updated properly by the implementation
        self.assertIn("x", call_block["accesses"]["writes"], "x should be in writes list")
    
    def test_sequential_inlining(self):
        """Test inlining of sequential internal function calls."""
        # Create mock blocks for caller: baz() { foo(); bar(); }
        caller_blocks = [
            {
                "id": "Block0",
                "statements": [
                    {"type": "FunctionCall", "node": {}},  # foo()
                    {"type": "FunctionCall", "node": {}}   # bar()
                ],
                "terminator": "return",
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": [
                    "ret_1 = call[internal](foo)",
                    "ret_2 = call[internal](bar)"
                ]
            }
        ]
        
        # Create mock blocks for foo: foo() { y = 2; }
        foo_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": [], "writes": ["y"]},
                "ssa_versions": {"reads": {}, "writes": {"y": 1}},
                "ssa_statements": ["y_1 = 2"]
            }
        ]
        
        # Create mock blocks for bar: bar() { x = 1; }
        bar_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": [], "writes": ["x"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = 1"]
            }
        ]
        
        # Mock function map and entrypoints data
        function_map = {"foo": MagicMock(), "bar": MagicMock()}
        entrypoints_data = [
            {
                "name": "baz",
                "basic_blocks": caller_blocks,
                "ssa": caller_blocks
            },
            {
                "name": "foo",
                "basic_blocks": foo_blocks,
                "ssa": foo_blocks
            },
            {
                "name": "bar",
                "basic_blocks": bar_blocks,
                "ssa": bar_blocks
            }
        ]
        
        # Call the function
        result_blocks = self.parser.inline_internal_calls(caller_blocks, function_map, entrypoints_data)
        
        # Verify the results
        self.assertEqual(len(result_blocks), 1, "Should have one block")
        
        # Check the SSA statements in the result
        ssa_statements = result_blocks[0]["ssa_statements"]
        self.assertEqual(len(ssa_statements), 4, "Should have 4 statements (2 inlined + 2 original calls)")
        
        # Both inlined statements should be present
        has_inlined_y = any("y_" in stmt and "= 2" in stmt for stmt in ssa_statements)
        has_inlined_x = any("x_" in stmt and "= 1" in stmt for stmt in ssa_statements)
        self.assertTrue(has_inlined_y, "Should have inlined y = 2 assignment")
        self.assertTrue(has_inlined_x, "Should have inlined x = 1 assignment")
        
        # Check that accesses were updated properly by the implementation
        self.assertIn("y", result_blocks[0]["accesses"]["writes"], "y should be in writes list")
        self.assertIn("x", result_blocks[0]["accesses"]["writes"], "x should be in writes list")

if __name__ == '__main__':
    unittest.main()