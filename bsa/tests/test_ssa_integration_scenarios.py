"""
Integration tests for SSA output in various Solidity code scenarios.
"""

import unittest
import tempfile
import os
import shutil
import json
from bsa.parser.ast_parser import ASTParser
from bsa.utils.forge import build_project_ast

class TestSSAIntegrationScenarios(unittest.TestCase):
    """Test the SSA integration with real-world scenarios."""
    
    def setUp(self):
        """Set up test environment with a temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.test_dir, "src")
        os.makedirs(self.src_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.test_dir)
    
    def create_solidity_file(self, filename, content):
        """Helper to create a Solidity file with given content."""
        file_path = os.path.join(self.src_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path
    
    def create_foundry_toml(self):
        """Create a basic foundry.toml configuration."""
        with open(os.path.join(self.test_dir, "foundry.toml"), "w") as f:
            f.write("""
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
            """)
    
    def test_if_statement_ssa(self):
        """Test SSA generation for a simple if statement."""
        # Check if forge is installed - this should always be true in a proper dev environment
        import shutil
        if shutil.which("forge") is None:
            self.fail("Forge not found! It should be installed for these tests to run.")
        # Create the test contract
        self.create_solidity_file("SimpleIf.sol", """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleIf {
    function test() public {
        uint x = 1;
        if (x > 0) {
            x = 2;
        }
    }
}
        """)
        
        # Create foundry.toml
        self.create_foundry_toml()
        
        # Build the project and parse
        self.assertTrue(build_project_ast(self.test_dir))
        parser = ASTParser(self.test_dir)
        contracts = parser.parse()
        
        # Find our test contract and function
        self.assertTrue(len(contracts) > 0)
        contract = next((c for c in contracts if c["contract"]["name"] == "SimpleIf"), None)
        self.assertIsNotNone(contract)
        
        # Find the test function
        entrypoint = next((e for e in contract["entrypoints"] if e["name"] == "test"), None)
        self.assertIsNotNone(entrypoint)
        
        # Verify SSA output exists and is correct
        self.assertTrue("ssa" in entrypoint)
        ssa_blocks = entrypoint["ssa"]
        
        # Check that we have at least 3 blocks: pre-if, if-true, and merge
        self.assertGreaterEqual(len(ssa_blocks), 3)
        
        # Check that we have the variable assignments in SSA form
        first_block = ssa_blocks[0]
        self.assertIn("x_1 = ", first_block["ssa_statements"][0])  # x = 1
        
        # Check that we have a conditional terminator
        has_conditional = False
        for block in ssa_blocks:
            if block["terminator"] and "if " in block["terminator"] and " then goto " in block["terminator"]:
                has_conditional = True
                break
        self.assertTrue(has_conditional, "No conditional terminator found")
    
    def test_for_loop_ssa(self):
        """Test SSA generation for a for loop."""
        # Check if forge is installed - this should always be true in a proper dev environment
        import shutil
        if shutil.which("forge") is None:
            self.fail("Forge not found! It should be installed for these tests to run.")
        # Create the test contract
        self.create_solidity_file("ForLoop.sol", """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ForLoop {
    function test() public {
        uint x = 0;
        for (uint i = 0; i < 2; i++) {
            x = i;
        }
    }
}
        """)
        
        # Create foundry.toml
        self.create_foundry_toml()
        
        # Build the project and parse
        self.assertTrue(build_project_ast(self.test_dir))
        parser = ASTParser(self.test_dir)
        contracts = parser.parse()
        
        # Find our test contract and function
        self.assertTrue(len(contracts) > 0)
        contract = next((c for c in contracts if c["contract"]["name"] == "ForLoop"), None)
        self.assertIsNotNone(contract)
        
        # Find the test function
        entrypoint = next((e for e in contract["entrypoints"] if e["name"] == "test"), None)
        self.assertIsNotNone(entrypoint)
        
        # Verify SSA output exists and is correct
        self.assertTrue("ssa" in entrypoint)
        ssa_blocks = entrypoint["ssa"]
        
        # Check that we have at least 4 blocks: init, header, body, exit
        self.assertGreaterEqual(len(ssa_blocks), 4)
        
        # Verify that we have phi functions in the header block
        has_phi = False
        for block in ssa_blocks:
            for stmt in block["ssa_statements"]:
                if "phi(" in stmt:
                    has_phi = True
                    break
            if has_phi:
                break
        self.assertTrue(has_phi, "No phi function found in loop header")
    
    def test_external_call_ssa(self):
        """Test SSA generation with an external call."""
        # Check if forge is installed - this should always be true in a proper dev environment
        import shutil
        if shutil.which("forge") is None:
            self.fail("Forge not found! It should be installed for these tests to run.")
        # Create the test contract
        self.create_solidity_file("ExternalCall.sol", """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IExample {
    function hello() external;
}

contract ExternalCall {
    function test(address a) public {
        uint x = 1;
        IExample(a).hello();
    }
}
        """)
        
        # Create foundry.toml
        self.create_foundry_toml()
        
        # Build the project and parse
        self.assertTrue(build_project_ast(self.test_dir))
        parser = ASTParser(self.test_dir)
        contracts = parser.parse()
        
        # Find our test contract and function
        self.assertTrue(len(contracts) > 0)
        contract = next((c for c in contracts if c["contract"]["name"] == "ExternalCall"), None)
        self.assertIsNotNone(contract)
        
        # Find the test function
        entrypoint = next((e for e in contract["entrypoints"] if e["name"] == "test"), None)
        self.assertIsNotNone(entrypoint)
        
        # Verify SSA output exists and is correct
        self.assertTrue("ssa" in entrypoint)
        ssa_blocks = entrypoint["ssa"]
        
        # Check for external call in SSA statements
        has_external_call = False
        for block in ssa_blocks:
            for stmt in block["ssa_statements"]:
                if "call[external]" in stmt and "hello" in stmt:
                    has_external_call = True
                    break
            if has_external_call:
                break
        self.assertTrue(has_external_call, "No external call found in SSA")
    
    def test_return_ssa(self):
        """Test SSA generation with a return statement."""
        # Check if forge is installed - this should always be true in a proper dev environment
        import shutil
        if shutil.which("forge") is None:
            self.fail("Forge not found! It should be installed for these tests to run.")
        # Create the test contract
        self.create_solidity_file("Return.sol", """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Return {
    function test() public {
        uint x = 1;
        return;
    }
}
        """)
        
        # Create foundry.toml
        self.create_foundry_toml()
        
        # Build the project and parse
        self.assertTrue(build_project_ast(self.test_dir))
        parser = ASTParser(self.test_dir)
        contracts = parser.parse()
        
        # Find our test contract and function
        self.assertTrue(len(contracts) > 0)
        contract = next((c for c in contracts if c["contract"]["name"] == "Return"), None)
        self.assertIsNotNone(contract)
        
        # Find the test function
        entrypoint = next((e for e in contract["entrypoints"] if e["name"] == "test"), None)
        self.assertIsNotNone(entrypoint)
        
        # Verify SSA output exists and is correct
        self.assertTrue("ssa" in entrypoint)
        ssa_blocks = entrypoint["ssa"]
        
        # Check that we have the return terminator
        has_return = False
        for block in ssa_blocks:
            if block["terminator"] == "return":
                has_return = True
                break
        self.assertTrue(has_return, "No return terminator found")

if __name__ == '__main__':
    unittest.main()