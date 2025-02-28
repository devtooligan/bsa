import unittest
from bsa.parser.ast_parser import ASTParser

class TestPhiFunctions(unittest.TestCase):
    def setUp(self):
        self.parser = ASTParser("./")
    
    def test_phi_for_variable_modified_in_one_branch(self):
        """Test phi function insertion for a variable modified in only one branch."""
        # Basic blocks for: function test() public { x = 1; if (x > 0) x = 2; y = x; }
        basic_blocks = [
            # Block0: x = 1; if (x > 0)...
            {
                "id": "Block0",
                "statements": [],
                "terminator": "if condition then goto Block1 else goto Block2",
                "accesses": {"reads": ["x"], "writes": ["x"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = ", "if (x_1)"]
            },
            # Block1: x = 2; (true branch)
            {
                "id": "Block1",
                "statements": [],
                "terminator": "goto Block2",
                "accesses": {"reads": [], "writes": ["x"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 2}},
                "ssa_statements": ["x_2 = "],
                "branch_type": "true"
            },
            # Block2: y = x; (merge point)
            {
                "id": "Block2",
                "statements": [],
                "terminator": None,
                "accesses": {"reads": ["x"], "writes": ["y"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"y": 1}},
                "ssa_statements": ["y_1 = x_1"]
            }
        ]
        
        # Insert phi functions
        blocks_with_phi = self.parser.insert_phi_functions(basic_blocks)
        
        # Find the merge block (Block2)
        merge_block = next(b for b in blocks_with_phi if b["id"] == "Block2")
        
        # Check if a phi function was added for x
        self.assertTrue(any("x_" in stmt and "phi" in stmt for stmt in merge_block["ssa_statements"]),
                      "Phi function for x should be added at merge point")
        
        # Check the first statement - should be the phi function
        phi_stmt = merge_block["ssa_statements"][0]
        self.assertIn("phi", phi_stmt, "First statement should be a phi function")
        self.assertIn("x_", phi_stmt, "Phi function should be for variable x")
        
        # The phi should reference both x_1 and x_2
        self.assertIn("x_1", phi_stmt, "Phi function should include x_1")
        self.assertIn("x_2", phi_stmt, "Phi function should include x_2")
        
        # Other statements should use the phi result, not the original variables
        for stmt in merge_block["ssa_statements"][1:]:
            if "x_1" in stmt:
                self.fail(f"Statement uses x_1 instead of phi result: {stmt}")
            if "x_2" in stmt:
                self.fail(f"Statement uses x_2 instead of phi result: {stmt}")
    
    def test_phi_for_variable_modified_in_both_branches(self):
        """Test phi function insertion for a variable modified in both branches."""
        # Basic blocks for: function test() public { x = 1; if (x > 0) y = 2; else y = 3; z = y; }
        basic_blocks = [
            # Block0: x = 1; if (x > 0)...
            {
                "id": "Block0",
                "statements": [],
                "terminator": "if condition then goto Block1 else goto Block2",
                "accesses": {"reads": ["x"], "writes": ["x"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = ", "if (x_1)"]
            },
            # Block1: y = 2; (true branch)
            {
                "id": "Block1",
                "statements": [],
                "terminator": "goto Block3",
                "accesses": {"reads": [], "writes": ["y"]},
                "ssa_versions": {"reads": {}, "writes": {"y": 1}},
                "ssa_statements": ["y_1 = "],
                "branch_type": "true"
            },
            # Block2: y = 3; (false branch)
            {
                "id": "Block2",
                "statements": [],
                "terminator": "goto Block3",
                "accesses": {"reads": [], "writes": ["y"]},
                "ssa_versions": {"reads": {}, "writes": {"y": 1}},
                "ssa_statements": ["y_1 = "],
                "branch_type": "false"
            },
            # Block3: z = y; (merge point)
            {
                "id": "Block3",
                "statements": [],
                "terminator": None,
                "accesses": {"reads": ["y"], "writes": ["z"]},
                "ssa_versions": {"reads": {"y": 1}, "writes": {"z": 1}},
                "ssa_statements": ["z_1 = y_1"]
            }
        ]
        
        # Insert phi functions
        blocks_with_phi = self.parser.insert_phi_functions(basic_blocks)
        
        # Find the merge block (Block3)
        merge_block = next(b for b in blocks_with_phi if b["id"] == "Block3")
        
        # Check if a phi function was added for y
        self.assertTrue(any("y_" in stmt and "phi" in stmt for stmt in merge_block["ssa_statements"]),
                      "Phi function for y should be added at merge point")
        
        # Check the first statement - should be the phi function
        phi_stmt = merge_block["ssa_statements"][0]
        self.assertIn("phi", phi_stmt, "First statement should be a phi function")
        self.assertIn("y_", phi_stmt, "Phi function should be for variable y")
        
        # The phi should reference y_1 from both branches
        self.assertIn("y_1", phi_stmt, "Phi function should include y_1")
        
        # Other statements should use the phi result, not the original variables
        self.assertNotEqual(merge_block["ssa_statements"][1], "z_1 = y_1", 
                          "Statement should use the phi result, not y_1")
    
    def test_phi_for_variables_with_control_flow_merges(self):
        """Test phi function insertion for variables defined before and inside control flow."""
        # Basic blocks for: function test() public { x = 1; if (x > 0) { x = 2; y = 3; } z = x; }
        basic_blocks = [
            # Block0: x = 1; if (x > 0)...
            {
                "id": "Block0",
                "statements": [],
                "terminator": "if condition then goto Block1 else goto Block2",
                "accesses": {"reads": ["x"], "writes": ["x"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = ", "if (x_1)"]
            },
            # Block1: x = 2; y = 3; (true branch)
            {
                "id": "Block1",
                "statements": [],
                "terminator": "goto Block2",
                "accesses": {"reads": [], "writes": ["x", "y"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 2, "y": 1}},
                "ssa_statements": ["x_2 = ", "y_1 = "],
                "branch_type": "true"
            },
            # Block2: z = x; (merge point)
            {
                "id": "Block2",
                "statements": [],
                "terminator": None,
                "accesses": {"reads": ["x"], "writes": ["z"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"z": 1}},
                "ssa_statements": ["z_1 = x_1"]
            }
        ]
        
        # Insert phi functions
        blocks_with_phi = self.parser.insert_phi_functions(basic_blocks)
        
        # Find the merge block (Block2)
        merge_block = next(b for b in blocks_with_phi if b["id"] == "Block2")
        
        # Check if a phi function was added for x
        self.assertTrue(any("x_" in stmt and "phi" in stmt for stmt in merge_block["ssa_statements"]),
                      "Phi function for x should be added at merge point")
        
        # Check if NO phi function was added for y (it's only defined in one branch)
        self.assertFalse(any("y_" in stmt and "phi" in stmt for stmt in merge_block["ssa_statements"]),
                       "Phi function for y should NOT be added at merge point")
        
        # Check the first statement - should be the phi function for x
        phi_stmt = merge_block["ssa_statements"][0]
        self.assertIn("phi", phi_stmt, "First statement should be a phi function")
        self.assertIn("x_", phi_stmt, "Phi function should be for variable x")
        
        # The phi should reference both x_1 and x_2
        self.assertIn("x_1", phi_stmt, "Phi function should include x_1")
        self.assertIn("x_2", phi_stmt, "Phi function should include x_2")
        
        # The z statement should use the phi result, not the original x_1
        self.assertNotEqual(merge_block["ssa_statements"][1], "z_1 = x_1", 
                           "Statement should use the phi result, not x_1")
    
    def test_phi_for_function_calls_in_branches(self):
        """Test phi function insertion when a function call is in one branch."""
        # Basic blocks for: function test() public { x = 1; if (x > 0) foo(); else x = 2; y = x; }
        basic_blocks = [
            # Block0: x = 1; if (x > 0)...
            {
                "id": "Block0",
                "statements": [],
                "terminator": "if condition then goto Block1 else goto Block2",
                "accesses": {"reads": ["x"], "writes": ["x"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = ", "if (x_1)"]
            },
            # Block1: foo(); (true branch)
            {
                "id": "Block1",
                "statements": [],
                "terminator": "goto Block3",
                "accesses": {"reads": [], "writes": []},
                "ssa_versions": {"reads": {}, "writes": {}},
                "ssa_statements": ["call(foo)"],
                "branch_type": "true"
            },
            # Block2: x = 2; (false branch)
            {
                "id": "Block2",
                "statements": [],
                "terminator": "goto Block3",
                "accesses": {"reads": [], "writes": ["x"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 2}},
                "ssa_statements": ["x_2 = "],
                "branch_type": "false"
            },
            # Block3: y = x; (merge point)
            {
                "id": "Block3",
                "statements": [],
                "terminator": None,
                "accesses": {"reads": ["x"], "writes": ["y"]},
                "ssa_versions": {"reads": {"x": 1}, "writes": {"y": 1}},
                "ssa_statements": ["y_1 = x_1"]
            }
        ]
        
        # Insert phi functions
        blocks_with_phi = self.parser.insert_phi_functions(basic_blocks)
        
        # Find the merge block (Block3)
        merge_block = next(b for b in blocks_with_phi if b["id"] == "Block3")
        
        # Check if a phi function was added for x
        self.assertTrue(any("x_" in stmt and "phi" in stmt for stmt in merge_block["ssa_statements"]),
                      "Phi function for x should be added at merge point")
        
        # Check the first statement - should be the phi function
        phi_stmt = merge_block["ssa_statements"][0]
        self.assertIn("phi", phi_stmt, "First statement should be a phi function")
        self.assertIn("x_", phi_stmt, "Phi function should be for variable x")
        
        # The phi should reference versions of x from both paths
        # The true branch path has no writes to x, so our algorithm might use x_0 or x_1
        self.assertTrue(
            any(f"x_{v}" in phi_stmt for v in [0, 1]),
            "Phi function should include version from true branch"
        )
        self.assertIn("x_2", phi_stmt, "Phi function should include x_2 from false branch")
        
        # Other statements should use the phi result, not the original variables
        # Get the new version from the phi function
        phi_parts = phi_stmt.split(' = phi(')[0]
        new_x_version = phi_parts.split('_')[1]  # Extract version number, eg. "3" from "x_3"
        
        # Check that the statement uses the new phi version
        self.assertIn(f"x_{new_x_version}", merge_block["ssa_statements"][1],
                    f"Statement should use phi result x_{new_x_version}, not x_1")

if __name__ == '__main__':
    unittest.main()