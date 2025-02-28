import unittest
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestLoops(unittest.TestCase):
    def setUp(self):
        self.parser = ASTParser("./")
    
    def test_for_loop_basic_blocks(self):
        """Test that for loops are correctly split into basic blocks."""
        # Mock a simple for loop
        for_loop = {
            "nodeType": "ForStatement",
            "initializationExpression": {
                "nodeType": "VariableDeclarationStatement",
                "declarations": [
                    {
                        "nodeType": "VariableDeclaration",
                        "name": "i",
                        "typeName": {"name": "uint256"}
                    }
                ],
                "initialValue": {"nodeType": "Literal", "value": "0"}
            },
            "condition": {
                "nodeType": "BinaryOperation",
                "operator": "<",
                "leftExpression": {"nodeType": "Identifier", "name": "i"},
                "rightExpression": {"nodeType": "Identifier", "name": "n"}
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
                    {
                        "nodeType": "ExpressionStatement",
                        "expression": {
                            "nodeType": "Assignment",
                            "operator": "+=",
                            "leftHandSide": {"nodeType": "Identifier", "name": "total"},
                            "rightHandSide": {"nodeType": "Identifier", "name": "i"}
                        }
                    }
                ]
            }
        }
        
        # Create a basic block with the for loop
        basic_blocks = [
            {
                "id": "Block0",
                "statements": [
                    {"type": "ForLoop", "node": for_loop}
                ],
                "terminator": "ForLoop"
            }
        ]
        
        # Refine the basic blocks with control flow
        refined_blocks = self.parser.refine_blocks_with_control_flow(basic_blocks)
        
        # Check that we have at least 5 blocks (init, header, body, increment, exit)
        self.assertGreaterEqual(len(refined_blocks), 5)
        
        # Check that we have the expected block types
        init_block = next((b for b in refined_blocks if b.get("is_loop_init", False)), None)
        header_block = next((b for b in refined_blocks if b.get("is_loop_header", False)), None)
        body_block = next((b for b in refined_blocks if b.get("is_loop_body", False)), None)
        increment_block = next((b for b in refined_blocks if b.get("is_loop_increment", False)), None)
        exit_block = next((b for b in refined_blocks if b.get("is_loop_exit", False)), None)
        
        # Verify each block exists
        self.assertIsNotNone(init_block, "Missing init block")
        self.assertIsNotNone(header_block, "Missing header block")
        self.assertIsNotNone(body_block, "Missing body block")
        self.assertIsNotNone(increment_block, "Missing increment block")
        self.assertIsNotNone(exit_block, "Missing exit block")
        
        # Check the control flow connections
        self.assertTrue(init_block["terminator"].startswith("goto"))
        self.assertTrue(header_block["terminator"].startswith("if"))
        self.assertTrue(body_block["terminator"].startswith("goto"))
        self.assertTrue(increment_block["terminator"].startswith("goto"))
        
        # Track variable accesses
        blocks_with_accesses = self.parser.track_variable_accesses(refined_blocks)
        
        # Check variable accesses in the init block
        self.assertIn("i", init_block["accesses"]["writes"], "Init block should write to 'i'")
        
        # Check variable accesses in the header block
        self.assertIn("i", header_block["accesses"]["reads"], "Header block should read 'i'")
        self.assertIn("n", header_block["accesses"]["reads"], "Header block should read 'n'")
        
        # Check variable accesses in the body block
        self.assertIn("total", body_block["accesses"]["writes"], "Body block should write to 'total'")
        self.assertIn("i", body_block["accesses"]["reads"], "Body block should read 'i'")
        
        # Check variable accesses in the increment block
        self.assertIn("i", increment_block["accesses"]["writes"], "Increment block should write to 'i'")
        self.assertIn("i", increment_block["accesses"]["reads"], "Increment block should read 'i'")
    
    def test_while_loop_basic_blocks(self):
        """Test that while loops are correctly split into basic blocks."""
        # Mock a simple while loop
        while_loop = {
            "nodeType": "WhileStatement",
            "condition": {
                "nodeType": "BinaryOperation",
                "operator": "<",
                "leftExpression": {"nodeType": "Identifier", "name": "i"},
                "rightExpression": {"nodeType": "Identifier", "name": "n"}
            },
            "body": {
                "nodeType": "Block",
                "statements": [
                    {
                        "nodeType": "ExpressionStatement",
                        "expression": {
                            "nodeType": "Assignment",
                            "operator": "+=",
                            "leftHandSide": {"nodeType": "Identifier", "name": "total"},
                            "rightHandSide": {"nodeType": "Identifier", "name": "i"}
                        }
                    },
                    {
                        "nodeType": "ExpressionStatement",
                        "expression": {
                            "nodeType": "UnaryOperation",
                            "operator": "++",
                            "subExpression": {"nodeType": "Identifier", "name": "i"}
                        }
                    }
                ]
            }
        }
        
        # Create a basic block with the while loop
        basic_blocks = [
            {
                "id": "Block0",
                "statements": [
                    {"type": "WhileLoop", "node": while_loop}
                ],
                "terminator": "WhileLoop"
            }
        ]
        
        # Refine the basic blocks with control flow
        refined_blocks = self.parser.refine_blocks_with_control_flow(basic_blocks)
        
        # Check that we have at least 4 blocks (pre, header, body, exit)
        self.assertGreaterEqual(len(refined_blocks), 4)
        
        # Check that we have the expected block types
        pre_block = refined_blocks[0]  # First block is pre-loop
        header_block = next((b for b in refined_blocks if b.get("is_loop_header", False)), None)
        body_block = next((b for b in refined_blocks if b.get("is_loop_body", False)), None)
        exit_block = next((b for b in refined_blocks if b.get("is_loop_exit", False)), None)
        
        # Verify each block exists
        self.assertIsNotNone(pre_block, "Missing pre-loop block")
        self.assertIsNotNone(header_block, "Missing header block")
        self.assertIsNotNone(body_block, "Missing body block")
        self.assertIsNotNone(exit_block, "Missing exit block")
        
        # Check the control flow connections
        self.assertTrue(pre_block["terminator"].startswith("goto"))
        self.assertTrue(header_block["terminator"].startswith("if"))
        self.assertTrue(body_block["terminator"].startswith("goto"), 
                       f"Body block terminator should start with 'goto', but got: {body_block['terminator']}")
        
        # Track variable accesses
        blocks_with_accesses = self.parser.track_variable_accesses(refined_blocks)
        
        # Check variable accesses in the header block
        self.assertIn("i", header_block["accesses"]["reads"], "Header block should read 'i'")
        self.assertIn("n", header_block["accesses"]["reads"], "Header block should read 'n'")
        
        # Check variable accesses in the body block - note that in our implementation,
        # the body block only has the "total += i" statement, while the "i++" is in the terminator,
        # so "i" isn't written in the body block
        self.assertIn("total", body_block["accesses"]["writes"], "Body block should write to 'total'")
        self.assertIn("i", body_block["accesses"]["reads"], "Body block should read 'i'")
    
    def test_phi_function_at_loop_header(self):
        """Test that phi functions are created at loop headers for variables that change in the loop."""
        # Similar to the for loop test, but we'll manually set up the control flow and variable accesses
        basic_blocks = [
            # Block0: Initialization
            {
                "id": "Block0",
                "statements": [],
                "terminator": "goto Block1",
                "accesses": {"reads": [], "writes": ["i", "total"]},
                "ssa_versions": {"reads": {}, "writes": {"i": 1, "total": 1}},
                "ssa_statements": ["i_1 = 0", "total_1 = 0"]
            },
            # Block1: Loop header (condition check)
            {
                "id": "Block1",
                "statements": [],
                "terminator": "if i < n then goto Block2 else goto Block4",
                "accesses": {"reads": ["i", "n"], "writes": []},
                "ssa_versions": {"reads": {"i": 1, "n": 0}, "writes": {}},
                "ssa_statements": ["if (i_1 < n_0)"],
                "is_loop_header": True
            },
            # Block2: Loop body
            {
                "id": "Block2",
                "statements": [],
                "terminator": "goto Block3",
                "accesses": {"reads": ["i", "total"], "writes": ["total"]},
                "ssa_versions": {"reads": {"i": 1, "total": 1}, "writes": {"total": 2}},
                "ssa_statements": ["total_2 = total_1 + i_1"],
                "is_loop_body": True
            },
            # Block3: Increment (with back-edge to header)
            {
                "id": "Block3",
                "statements": [],
                "terminator": "goto Block1",  # Back-edge to header
                "accesses": {"reads": ["i"], "writes": ["i"]},
                "ssa_versions": {"reads": {"i": 1}, "writes": {"i": 2}},
                "ssa_statements": ["i_2 = i_1 + 1"],
                "is_loop_increment": True
            },
            # Block4: Exit
            {
                "id": "Block4",
                "statements": [],
                "terminator": None,
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": [],
                "is_loop_exit": True
            }
        ]
        
        # Insert phi functions
        blocks_with_phi = self.parser.insert_phi_functions(basic_blocks)
        
        # Check that a phi function was added to the loop header
        header_block = next(b for b in blocks_with_phi if b["id"] == "Block1")
        
        # The header should have phi functions for i (between i_1 and i_2 from the increment)
        self.assertTrue(any("i_" in stmt and "phi" in stmt for stmt in header_block["ssa_statements"]), 
                       f"Loop header should have phi function for i, but got: {header_block['ssa_statements']}")
        
        # Check if the phi function references the correct versions
        phi_stmt = next((stmt for stmt in header_block["ssa_statements"] if "phi" in stmt and "i_" in stmt), None)
        self.assertIsNotNone(phi_stmt, "Missing phi function for i in header block")
        
        # The i phi function should combine i_1 (initial) and i_2 (from increment)
        # Something like: i_3 = phi(i_1, i_2)
        self.assertIn("i_1", phi_stmt, f"Phi function should include i_1: {phi_stmt}")
        self.assertIn("i_2", phi_stmt, f"Phi function should include i_2: {phi_stmt}")

if __name__ == '__main__':
    unittest.main()