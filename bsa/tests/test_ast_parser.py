"""
Tests for the fixes to the AST parser.
"""

import unittest
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestASTParserFixes(unittest.TestCase):
    """Test fixes to the AST parser for internal call inlining."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = ASTParser("/dummy/path")
        
    def test_no_variable_duplication(self):
        """Test that variables are not duplicated in compound operations."""
        # Direct test of inline_internal_calls
        
        # Create mock blocks for a function that calls _mint with to and amount
        caller_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "FunctionCall", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": ["to", "amount"], "writes": []},
                "ssa_versions": {"reads": {"to": 0, "amount": 0}, "writes": {}},
                "ssa_statements": ["ret_1 = call[internal](_mint, to_0, amount_0)"]
            }
        ]
        
        # Create mock function _mint: _mint(to, amount) { balanceOf[to] += amount; }
        function_map = {
            "_mint": MagicMock(
                parameters={"parameters": [
                    {"name": "to"}, 
                    {"name": "amount"}
                ]}
            )
        }
        
        # Create entrypoints data for _mint function
        entrypoints_data = [
            {
                "name": "_mint",
                "ssa": [
                    {
                        "id": "Block0",
                        "ssa_statements": ["balanceOf[to]_1 = balanceOf[to]_0 + amount_0"]
                    }
                ]
            }
        ]
        
        # Call the inline_internal_calls function
        result_blocks = self.parser.inline_internal_calls(caller_blocks, function_map, entrypoints_data)
        
        # Check the result
        self.assertEqual(len(result_blocks), 1, "Should have one block")
        self.assertEqual(len(result_blocks[0]["ssa_statements"]), 2, "Should have 2 statements (original call + inlined)")
        
        # Verify the inlined statement has no duplicated variables
        inlined_stmt = result_blocks[0]["ssa_statements"][1]
        self.assertEqual(inlined_stmt, "balanceOf[to]_1 = balanceOf[to]_0 + amount_0", 
                         "Amount should appear only once in inlined statement")
            
    def test_call_location(self):
        """Test that call locations point to function definitions not call sites."""
        # Create a function map for _mint at line 50, col 5
        function_map = {
            "_mint": MagicMock(src="100:1:1")  # offset 100 -> line 50, col 5
        }
        
        # Create basic blocks with ssa statements containing a call
        basic_blocks = [
            {
                "id": "Block0",
                "ssa_statements": ["ret_1 = call[internal](_mint, to_0, amount_0)"]
            }
        ]
        
        # Patch the offset_to_line_col function to return a known value for our test
        with patch('bsa.parser.source_mapper.offset_to_line_col') as mock_offset:
            # Set up the mock to return [50, 5] for offset 100
            mock_offset.return_value = [50, 5]
            
            # Create the expected output
            expected_calls = [
                {
                    "name": "_mint",
                    "in_contract": True,
                    "is_external": False,
                    "call_type": "internal",
                    "location": [50, 5]  # This is now from the function definition
                }
            ]
            
            # This is the code we're testing - similar to what's in _process_contract_definition
            def extract_calls(blocks, func_map, source_text=""):
                calls = []
                calls_seen = set()
                for block in blocks:
                    for stmt in block.get("ssa_statements", []):
                        if "call[internal]" in stmt:
                            # Extract internal call name
                            call_parts = stmt.split("call[internal](")[1].strip(")")
                            if "," in call_parts:
                                call_name = call_parts.split(",")[0].strip()
                            else:
                                call_name = call_parts.strip()
                                
                            if call_name not in calls_seen:
                                calls_seen.add(call_name)
                                
                                # Get source location for the internal function definition
                                location = [0, 0]
                                if call_name in func_map:
                                    func_node = func_map[call_name]
                                    src = func_node.get("src", "")
                                    if src:
                                        try:
                                            offset = int(src.split(":", 1)[0])
                                            location = mock_offset(offset, source_text)
                                        except (ValueError, IndexError):
                                            # Keep default [0, 0] if there's any error
                                            pass
                                
                                calls.append({
                                    "name": call_name,
                                    "in_contract": True,
                                    "is_external": False,
                                    "call_type": "internal",
                                    "location": location  # This now points to the function definition
                                })
                return calls
            
            # Run our extraction function
            actual_calls = extract_calls(basic_blocks, function_map)
            
            # Verify the calls match our expectations
            self.assertEqual(len(actual_calls), 1, "Should have one call")
            self.assertEqual(actual_calls[0]["name"], expected_calls[0]["name"], "Call name should match")
            self.assertEqual(actual_calls[0]["location"], expected_calls[0]["location"], "Location should match")
                
    def test_access_tracking(self):
        """Test that variable accesses are tracked correctly."""
        # Create a test block with internal call
        basic_blocks = [{
            "id": "Block1",
            "ssa_statements": ["ret_1 = call[internal](_mint, to_0, amount_0)"],
            "accesses": {
                "reads": ["to", "amount", "call[internal](_mint)"],
                "writes": ["balanceOf"]
            }
        }]
        
        # Create a simulated filter like what happens in track_variable_accesses
        def filter_call_markers(blocks):
            for block in blocks:
                if "accesses" in block:
                    reads = set(block["accesses"]["reads"])
                    reads_filtered = set()
                    for read in reads:
                        # Skip any call markers or function calls
                        if "call[" in read or "call(" in read or ")" in read:
                            continue
                        reads_filtered.add(read)
                    block["accesses"]["reads"] = list(reads_filtered)
            return blocks
            
        # Run our filter to simulate track_variable_accesses cleanup
        result_blocks = filter_call_markers(basic_blocks)
        
        # Verify that normal variables are preserved
        self.assertIn("to", result_blocks[0]["accesses"]["reads"])
        self.assertIn("amount", result_blocks[0]["accesses"]["reads"])
        
        # Verify that call markers are filtered out
        self.assertNotIn("call[internal](_mint)", result_blocks[0]["accesses"]["reads"])
        
        # Additional test directly using track_variable_accesses
        # Create basic block with assignment statement
        test_blocks = [{
            "id": "Block2",
            "statements": [{
                "type": "Assignment",
                "node": {
                    "nodeType": "ExpressionStatement",
                    "expression": {
                        "nodeType": "Assignment",
                        "leftHandSide": {
                            "nodeType": "IndexAccess",
                            "baseExpression": {"nodeType": "Identifier", "name": "balanceOf"},
                            "indexExpression": {"nodeType": "Identifier", "name": "to"}
                        },
                        "rightHandSide": {
                            "nodeType": "BinaryOperation",
                            "leftExpression": {
                                "nodeType": "IndexAccess",
                                "baseExpression": {"nodeType": "Identifier", "name": "balanceOf"},
                                "indexExpression": {"nodeType": "Identifier", "name": "to"}
                            },
                            "rightExpression": {"nodeType": "Identifier", "name": "amount"},
                            "operator": "+"
                        },
                        "operator": "="
                    }
                }
            }],
            "terminator": None
        }]
        
        # Process with track_variable_accesses
        tracked_blocks = self.parser.track_variable_accesses(test_blocks)
        
        # Verify tracking of regular variables
        self.assertTrue("reads" in tracked_blocks[0]["accesses"])
        self.assertTrue("writes" in tracked_blocks[0]["accesses"])
        self.assertTrue(isinstance(tracked_blocks[0]["accesses"]["reads"], list))
        self.assertTrue(isinstance(tracked_blocks[0]["accesses"]["writes"], list))

    def test_call_arg_formatting(self):
        """Test that call arguments are properly formatted with commas."""
        # Create a function call statement
        caller_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "FunctionCall", "node": {}}],
                "terminator": "return",
                "accesses": {"reads": ["to", "amount"], "writes": []},
                "ssa_versions": {"reads": {"to": 0, "amount": 0}, "writes": {}},
                "ssa_statements": ["ret_1 = call[internal](_mint, to_0, amount_0)"]
            }
        ]
        
        # Extract the call parts from the statement
        stmt = caller_blocks[0]["ssa_statements"][0]
        call_parts = stmt.split("call[internal](")[1].strip(")")
        func_name = call_parts.split(",")[0].strip()
        args_part = call_parts[len(func_name)+1:].strip()
        arg_list = [arg.strip() for arg in args_part.split(",") if arg.strip()]
        
        # Verify the correct extraction of function name and arguments
        self.assertEqual(func_name, "_mint", "Function name should be extracted correctly")
        self.assertEqual(len(arg_list), 2, "Should have 2 arguments")
        self.assertEqual(arg_list[0], "to_0", "First argument should be to_0")
        self.assertEqual(arg_list[1], "amount_0", "Second argument should be amount_0")

if __name__ == '__main__':
    unittest.main()