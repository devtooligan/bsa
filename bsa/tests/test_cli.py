import os
import subprocess
import glob
import json
import builtins
from unittest.mock import patch, call, mock_open
from click.testing import CliRunner
from bsa.cli import main, ASTNode

def test_main_with_nonexistent_path():
    """Test that the main function correctly identifies a non-existent path."""
    runner = CliRunner()
    # Use a path that definitely does not exist
    nonexistent_path = "./nonexistent_directory_12345"
    result = runner.invoke(main, [nonexistent_path])
    assert result.exit_code == 0
    assert "BSA is running!" in result.output
    assert f"Path does not exist: {nonexistent_path}" in result.output

def test_ast_node_class():
    """Test the ASTNode class initialization and properties."""
    # Test with nodeType present
    node_data = {"nodeType": "SourceUnit", "id": 1}
    node = ASTNode(node_data)
    assert node.node_type == "SourceUnit"
    assert node.data == node_data
    
    # Test with nodeType missing
    node_data = {"id": 1}
    node = ASTNode(node_data)
    assert node.node_type == "Unknown"
    assert node.data == node_data

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_functions_in_contract(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function finds function definitions inside contract nodes."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract node containing function nodes
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "doStuff",
                            "id": 2
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "anotherFunc",
                            "id": 3
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "BSA is running!" in result.output
    assert "Parsed node: ContractDefinition" in result.output
    assert "No Entrypoints found" in result.output  # No entrypoints because functions lack visibility
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_contract_no_functions(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function correctly handles contracts with no functions."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract node with empty nodes list
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": []
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "No Entrypoints found" in result.output
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_function_without_name(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function handles function definitions without names correctly."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract containing a function without name
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "id": 2
                            # No name field
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "No Entrypoints found" in result.output
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_multiple_contracts(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function can find functions from multiple contracts."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with multiple contract nodes
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract1",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "doStuff",
                            "id": 2,
                            "visibility": "external"
                        }
                    ]
                },
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract2",
                    "id": 3,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "anotherFunc",
                            "id": 4,
                            "visibility": "public"
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "Entrypoint: doStuff" in result.output
    assert "Entrypoint: anotherFunc" in result.output
    assert "No internal calls" in result.output
    # Note: For backward compatibility, Contract still shows just the first one
    assert "Contract: TestContract1" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_non_function_nodes(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function correctly filters out non-function nodes in a contract."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract containing mixed nodes
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "VariableDeclaration",
                            "name": "myVar",
                            "id": 2
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "myFunction",
                            "id": 3,
                            "visibility": "public"
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "Entrypoint: myFunction" in result.output
    assert "No internal calls" in result.output
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_empty_nodes_list(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function handles an empty nodes list correctly."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with an empty nodes list
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": []
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed AST node with type: SourceUnit" in result.output
    assert "No Entrypoints found" in result.output
    assert "Contract: Unknown" in result.output
    # Verify no Parsed node: lines are present
    assert "Parsed node:" not in result.output

@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_no_ast_files(mock_run, mock_glob):
    """Test that the main function handles case where no AST files are found."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return an empty list (no files found)
    mock_glob.return_value = []
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "BSA is running!" in result.output
    assert f"Built ASTs in: {existing_path}" in result.output
    assert "Found 0 AST files" in result.output
    assert "No AST files found" in result.output

@patch('subprocess.run')
def test_main_with_forge_clean_failure(mock_run):
    """Test that the main function handles forge clean failures correctly."""
    # Configure the mock to raise a CalledProcessError (failure case)
    error = subprocess.CalledProcessError(returncode=1, cmd=["forge", "clean"])
    mock_run.side_effect = error
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "BSA is running!" in result.output
    assert "Command failed:" in result.output
    
    # Verify subprocess.run was called with the correct arguments
    mock_run.assert_called_once_with(["forge", "clean"], cwd=existing_path, check=True)

@patch('subprocess.run')
def test_main_with_forge_build_failure(mock_run):
    """Test that the main function handles forge build failures correctly."""
    # Configure the mock to only raise an exception on the second call
    error = subprocess.CalledProcessError(returncode=1, cmd=["forge", "build", "--ast"])
    mock_run.side_effect = [
        subprocess.CompletedProcess(args=["forge", "clean"], returncode=0),
        error
    ]
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "BSA is running!" in result.output
    assert "Command failed:" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_entrypoints(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function correctly identifies external and public functions as entrypoints."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract containing functions with various visibilities
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "externalFunc",
                            "id": 2,
                            "visibility": "external",
                            "body": {
                                "statements": []
                            }
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "publicFunc",
                            "id": 3,
                            "visibility": "public",
                            "body": {
                                "statements": []
                            }
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "internalFunc",
                            "id": 4,
                            "visibility": "internal"
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "privateFunc",
                            "id": 5,
                            "visibility": "private"
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "Entrypoint: externalFunc" in result.output
    assert "Entrypoint: publicFunc" in result.output
    assert "No internal calls" in result.output
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_no_entrypoints(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function correctly identifies when there are no external or public functions."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract containing only internal functions
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "internalFunc1",
                            "id": 2,
                            "visibility": "internal"
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "privateFunc1",
                            "id": 3,
                            "visibility": "private"
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "No Entrypoints found" in result.output
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_internal_calls(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function correctly identifies internal function calls within entrypoints."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract containing 
    # a function that calls another internal function
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "doStuff",
                            "id": 2,
                            "visibility": "external",
                            "body": {
                                "statements": [
                                    {
                                        "nodeType": "FunctionCall",
                                        "expression": {
                                            "nodeType": "Identifier",
                                            "name": "helper"
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "helper",
                            "id": 3,
                            "visibility": "internal"
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "Entrypoint: doStuff" in result.output
    assert "Internal calls: helper" in result.output
    assert "Contract: TestContract" in result.output

@patch('json.load')
@patch('builtins.open', new_callable=mock_open)
@patch('glob.glob')
@patch('subprocess.run')
def test_main_with_multiple_internal_calls(mock_run, mock_glob, mock_file, mock_json_load):
    """Test that the main function correctly identifies multiple internal function calls within entrypoints."""
    # Configure the subprocess mock to return without raising an exception
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    
    # Configure the glob mock to return a fake JSON file
    fake_ast_file = "out/contracts/A.json"
    mock_glob.return_value = [fake_ast_file]
    
    # Configure the json.load mock to return a dictionary with a contract containing 
    # a function that calls multiple internal functions
    ast_data = {
        "ast": {
            "nodeType": "SourceUnit",
            "nodes": [
                {
                    "nodeType": "ContractDefinition",
                    "name": "TestContract",
                    "id": 1,
                    "nodes": [
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "processTransaction",
                            "id": 2,
                            "visibility": "external",
                            "body": {
                                "statements": [
                                    {
                                        "nodeType": "FunctionCall",
                                        "expression": {
                                            "nodeType": "Identifier",
                                            "name": "validateInput"
                                        }
                                    },
                                    {
                                        "nodeType": "ExpressionStatement",
                                        "expression": {
                                            "nodeType": "Assignment"
                                        }
                                    },
                                    {
                                        "nodeType": "FunctionCall",
                                        "expression": {
                                            "nodeType": "Identifier",
                                            "name": "updateState"
                                        }
                                    },
                                    {
                                        "nodeType": "FunctionCall",
                                        "expression": {
                                            "nodeType": "Identifier",
                                            "name": "emitEvent"
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "validateInput",
                            "id": 3,
                            "visibility": "internal"
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "updateState",
                            "id": 4,
                            "visibility": "internal"
                        },
                        {
                            "nodeType": "FunctionDefinition",
                            "name": "emitEvent",
                            "id": 5,
                            "visibility": "internal"
                        }
                    ]
                }
            ]
        }
    }
    mock_json_load.return_value = ast_data
    
    runner = CliRunner()
    existing_path = "./bsa"
    result = runner.invoke(main, [existing_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Parsed node: ContractDefinition" in result.output
    assert "Entrypoint: processTransaction" in result.output
    assert "Internal calls: validateInput, updateState, emitEvent" in result.output
    assert "Contract: TestContract" in result.output