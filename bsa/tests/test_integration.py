import os
import shutil
import pytest
from click.testing import CliRunner
from bsa.cli import main

@pytest.fixture
def setup_teardown_temp_project():
    """Setup and teardown a temporary Foundry project for testing."""
    # Setup
    temp_dir = "./temp_test"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create foundry.toml
    with open(os.path.join(temp_dir, "foundry.toml"), "w") as f:
        f.write("[profile.default]\nsrc = \"src\"\nout = \"out\"")
    
    # Create src directory and a test contract
    src_dir = os.path.join(temp_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    
    with open(os.path.join(src_dir, "Test.sol"), "w") as f:
        f.write("""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract Test {
  uint x;
  
  function doStuff() external {
    helper();
  }
  
  function helper() internal {}
}""")
    
    yield temp_dir
    
    # Teardown
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_full_parser_run(setup_teardown_temp_project):
    """Test the full BSA parser flow with a temporary Foundry project."""
    temp_dir = setup_teardown_temp_project
    
    runner = CliRunner()
    result = runner.invoke(main, [temp_dir])
    
    # Verify the output
    assert result.exit_code == 0
    assert "Contract: Test" in result.output
    assert "Entrypoint: doStuff at line" in result.output 
    assert "Internal calls: helper (this contract) at line" in result.output

def test_no_src_files(setup_teardown_temp_project):
    """Test the parser's behavior when there are no src files."""
    temp_dir = setup_teardown_temp_project
    
    # Remove the src directory
    shutil.rmtree(os.path.join(temp_dir, "src"), ignore_errors=True)
    
    runner = CliRunner()
    result = runner.invoke(main, [temp_dir])
    
    # Verify the output
    assert result.exit_code == 0
    assert "No src/ AST files found" in result.output

def test_bad_path():
    """Test the parser's behavior with a non-existent path."""
    nonexistent_path = "./nope"
    
    # Ensure the path doesn't exist
    if os.path.exists(nonexistent_path):
        shutil.rmtree(nonexistent_path)
    
    runner = CliRunner()
    result = runner.invoke(main, [nonexistent_path])
    
    # Verify the output
    assert result.exit_code == 0
    assert f"Path does not exist: {nonexistent_path}" in result.output