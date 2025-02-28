import os
import unittest
from unittest.mock import patch, mock_open
import json
from click.testing import CliRunner
from bsa.cli import main

class TestReentrancy(unittest.TestCase):
    @patch('json.load')
    @patch('builtins.open')
    @patch('glob.glob')
    @patch('subprocess.run')
    def test_reentrancy_found(self, mock_run, mock_glob, mock_open_func, mock_json_load):
        """Test that the reentrancy detector finds vulnerabilities with external calls before state variable writes."""
        # Configure the subprocess mock to return without raising an exception
        from subprocess import CompletedProcess
        mock_run.return_value = CompletedProcess(args=[], returncode=0)
        
        # Configure the glob mock to return test files
        src_file_path = "./bsa/src/Test.sol"
        ast_file_path = "./bsa/out/Test.sol/Test.json"
        
        # Setup glob.glob side effects for different calls
        mock_glob.side_effect = [
            [src_file_path],           # First call - src/*.sol
            ["./bsa/out/Test.sol"],    # Second call - out/*.sol
            [ast_file_path]            # Third call - out/Test.sol/*.json
        ]
        
        # Sample Solidity content for a contract with reentrancy vulnerability
        sol_content = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Test {
  uint x;
  
  function doStuff() external {
    // Vulnerability: external call before state write
    address(0x123).call("");
    x = 5;
  }
}"""
        
        # Configure the json.load mock to return AST with a reentrancy vulnerability
        ast_data = {
            "ast": {
                "nodeType": "SourceUnit",
                "nodes": [
                    {
                        "nodeType": "PragmaDirective",
                        "literals": ["solidity", "^", "0.8", ".13"],
                        "src": "39:24:0"
                    },
                    {
                        "nodeType": "ContractDefinition",
                        "name": "Test",
                        "id": 1,
                        "nodes": [
                            {
                                "nodeType": "VariableDeclaration",
                                "name": "x",
                                "id": 2,
                                "stateVariable": True,
                                "typeName": {
                                    "name": "uint"
                                },
                                "src": "85:6:0"
                            },
                            {
                                "nodeType": "FunctionDefinition",
                                "name": "doStuff",
                                "id": 3,
                                "visibility": "external",
                                "src": "95:100:0",
                                "body": {
                                    "statements": [
                                        {
                                            "nodeType": "ExpressionStatement",
                                            "src": "150:20:0",
                                            "expression": {
                                                "nodeType": "FunctionCall",
                                                "src": "150:20:0",
                                                "expression": {
                                                    "nodeType": "MemberAccess",
                                                    "memberName": "call",
                                                    "src": "150:15:0"
                                                }
                                            }
                                        },
                                        {
                                            "nodeType": "ExpressionStatement",
                                            "src": "180:5:0",
                                            "expression": {
                                                "nodeType": "Assignment",
                                                "leftHandSide": {
                                                    "nodeType": "Identifier",
                                                    "name": "x",
                                                    "src": "180:1:0"
                                                },
                                                "src": "180:5:0"
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
        
        # Configure mock_open to handle file reads
        m = mock_open()
        m.side_effect = [
            mock_open(read_data=sol_content).return_value,  # For the .sol file
            mock_open(read_data="{}").return_value  # For the .json file
        ]
        mock_open_func.side_effect = m
        
        # Configure json.load to return our AST data
        mock_json_load.return_value = ast_data
        
        # Run the CLI with our mocked environment
        runner = CliRunner()
        existing_path = "./bsa"
        result = runner.invoke(main, [existing_path])
        
        # Verify reentrancy is detected
        self.assertEqual(result.exit_code, 0)
        self.assertIn("!!!! REENTRANCY found in Test.doStuff", result.output)

    @patch('json.load')
    @patch('builtins.open')
    @patch('glob.glob')
    @patch('subprocess.run')
    def test_no_reentrancy_state_before_call(self, mock_run, mock_glob, mock_open_func, mock_json_load):
        """Test that no reentrancy is reported when state writes happen before external calls."""
        # Configure the subprocess mock to return without raising an exception
        from subprocess import CompletedProcess
        mock_run.return_value = CompletedProcess(args=[], returncode=0)
        
        # Configure the glob mock to return test files
        src_file_path = "./bsa/src/Test.sol"
        ast_file_path = "./bsa/out/Test.sol/Test.json"
        
        # Setup glob.glob side effects for different calls
        mock_glob.side_effect = [
            [src_file_path],           # First call - src/*.sol
            ["./bsa/out/Test.sol"],    # Second call - out/*.sol
            [ast_file_path]            # Third call - out/Test.sol/*.json
        ]
        
        # Sample Solidity content for a contract without reentrancy vulnerability (state write before call)
        sol_content = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Test {
  uint x;
  
  function noReentrancy() external {
    // No vulnerability: state write before external call
    x = 5;
    address(0x123).call("");
  }
}"""
        
        # Configure the json.load mock to return AST with no reentrancy vulnerability
        ast_data = {
            "ast": {
                "nodeType": "SourceUnit",
                "nodes": [
                    {
                        "nodeType": "PragmaDirective",
                        "literals": ["solidity", "^", "0.8", ".13"],
                        "src": "39:24:0"
                    },
                    {
                        "nodeType": "ContractDefinition",
                        "name": "Test",
                        "id": 1,
                        "nodes": [
                            {
                                "nodeType": "VariableDeclaration",
                                "name": "x",
                                "id": 2,
                                "stateVariable": True,
                                "typeName": {
                                    "name": "uint"
                                },
                                "src": "85:6:0"
                            },
                            {
                                "nodeType": "FunctionDefinition",
                                "name": "noReentrancy",
                                "id": 3,
                                "visibility": "external",
                                "src": "95:110:0",
                                "body": {
                                    "statements": [
                                        {
                                            "nodeType": "ExpressionStatement",
                                            "src": "150:5:0",
                                            "expression": {
                                                "nodeType": "Assignment",
                                                "leftHandSide": {
                                                    "nodeType": "Identifier",
                                                    "name": "x",
                                                    "src": "150:1:0"
                                                },
                                                "src": "150:5:0"
                                            }
                                        },
                                        {
                                            "nodeType": "ExpressionStatement",
                                            "src": "165:20:0",
                                            "expression": {
                                                "nodeType": "FunctionCall",
                                                "src": "165:20:0",
                                                "expression": {
                                                    "nodeType": "MemberAccess",
                                                    "memberName": "call",
                                                    "src": "165:15:0"
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
        
        # Configure mock_open to handle file reads
        m = mock_open()
        m.side_effect = [
            mock_open(read_data=sol_content).return_value,  # For the .sol file
            mock_open(read_data="{}").return_value  # For the .json file
        ]
        mock_open_func.side_effect = m
        
        # Configure json.load to return our AST data
        mock_json_load.return_value = ast_data
        
        # Run the CLI with our mocked environment
        runner = CliRunner()
        existing_path = "./bsa"
        result = runner.invoke(main, [existing_path])
        
        # Verify no reentrancy is detected
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("REENTRANCY found", result.output)

    @patch('json.load')
    @patch('builtins.open')
    @patch('glob.glob')
    @patch('subprocess.run')
    def test_no_reentrancy_no_state_write(self, mock_run, mock_glob, mock_open_func, mock_json_load):
        """Test that no reentrancy is reported when there are no state writes after external calls."""
        # Configure the subprocess mock to return without raising an exception
        from subprocess import CompletedProcess
        mock_run.return_value = CompletedProcess(args=[], returncode=0)
        
        # Configure the glob mock to return test files
        src_file_path = "./bsa/src/Test.sol"
        ast_file_path = "./bsa/out/Test.sol/Test.json"
        
        # Setup glob.glob side effects for different calls
        mock_glob.side_effect = [
            [src_file_path],           # First call - src/*.sol
            ["./bsa/out/Test.sol"],    # Second call - out/*.sol
            [ast_file_path]            # Third call - out/Test.sol/*.json
        ]
        
        # Sample Solidity content for a contract without reentrancy vulnerability (no state writes)
        sol_content = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Test {
  uint x;
  
  function noReentrancy() external {
    // No vulnerability: external call with no subsequent state write
    address(0x123).call("");
    // No state variables modified after the call
  }
}"""
        
        # Configure the json.load mock to return AST with no reentrancy vulnerability
        ast_data = {
            "ast": {
                "nodeType": "SourceUnit",
                "nodes": [
                    {
                        "nodeType": "PragmaDirective",
                        "literals": ["solidity", "^", "0.8", ".13"],
                        "src": "39:24:0"
                    },
                    {
                        "nodeType": "ContractDefinition",
                        "name": "Test",
                        "id": 1,
                        "nodes": [
                            {
                                "nodeType": "VariableDeclaration",
                                "name": "x",
                                "id": 2,
                                "stateVariable": True,
                                "typeName": {
                                    "name": "uint"
                                },
                                "src": "85:6:0"
                            },
                            {
                                "nodeType": "FunctionDefinition",
                                "name": "noReentrancy",
                                "id": 3,
                                "visibility": "external",
                                "src": "95:110:0",
                                "body": {
                                    "statements": [
                                        {
                                            "nodeType": "ExpressionStatement",
                                            "src": "150:20:0",
                                            "expression": {
                                                "nodeType": "FunctionCall",
                                                "src": "150:20:0",
                                                "expression": {
                                                    "nodeType": "MemberAccess",
                                                    "memberName": "call",
                                                    "src": "150:15:0"
                                                }
                                            }
                                        }
                                        # No state variable assignment after the call
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        # Configure mock_open to handle file reads
        m = mock_open()
        m.side_effect = [
            mock_open(read_data=sol_content).return_value,  # For the .sol file
            mock_open(read_data="{}").return_value  # For the .json file
        ]
        mock_open_func.side_effect = m
        
        # Configure json.load to return our AST data
        mock_json_load.return_value = ast_data
        
        # Run the CLI with our mocked environment
        runner = CliRunner()
        existing_path = "./bsa"
        result = runner.invoke(main, [existing_path])
        
        # Verify no reentrancy is detected
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("REENTRANCY found", result.output)

if __name__ == '__main__':
    unittest.main()