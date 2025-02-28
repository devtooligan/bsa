"""
Utilities for interacting with Forge, the Foundry Solidity development framework.
"""

import os
import subprocess
import glob
import json

def run_forge_command(command, project_path, check=True):
    """
    Run a forge command in the given project path.
    
    Args:
        command (list): The command to run, e.g. ["forge", "build", "--ast"]
        project_path (str): Path to the project directory
        check (bool): Whether to check the return code
        
    Returns:
        subprocess.CompletedProcess: The result of the command
        
    Raises:
        subprocess.CalledProcessError: If the command fails and check is True
    """
    return subprocess.run(command, cwd=project_path, check=check)

def clean_project(project_path):
    """
    Clean the Forge project by removing build artifacts.
    
    Args:
        project_path (str): Path to the project directory
        
    Returns:
        bool: True if successful, False if the command failed
    """
    try:
        run_forge_command(["forge", "clean"], project_path)
        return True
    except subprocess.CalledProcessError:
        return False

def build_project_ast(project_path):
    """
    Build the project and generate AST.
    
    Args:
        project_path (str): Path to the project directory
        
    Returns:
        bool: True if successful, False if the command failed
    """
    try:
        run_forge_command(["forge", "build", "--ast"], project_path)
        return True
    except subprocess.CalledProcessError:
        return False

def find_source_files(project_path):
    """
    Find all Solidity source files in the project.
    
    Args:
        project_path (str): Path to the project directory
        
    Returns:
        dict: Dictionary mapping contract names to file paths
    """
    src_dir = os.path.join(project_path, "src")
    sol_files = glob.glob(os.path.join(src_dir, "*.sol"))
    
    # Extract base filenames without .sol extension
    src_files = []
    src_file_paths = {}  # Map contract names to their source file paths
    for file_path in sol_files:
        base_name = os.path.basename(file_path)
        if base_name.endswith(".sol"):
            contract_name = base_name[:-4]  # Remove .sol extension
            src_files.append(contract_name)
            src_file_paths[contract_name] = file_path
    
    return src_file_paths

def find_ast_files(project_path, src_files):
    """
    Find AST files corresponding to the source files.
    
    Args:
        project_path (str): Path to the project directory
        src_files (list): List of source file names without extension
        
    Returns:
        list: List of AST JSON file paths
    """
    out_dir = os.path.join(project_path, "out")
    json_files = []
    
    # Look for directories in out/ that match our src files
    sol_dirs = glob.glob(os.path.join(out_dir, "*.sol"))
    for dir_path in sol_dirs:
        base_name = os.path.basename(dir_path)
        if base_name.endswith(".sol"):
            contract_name = base_name[:-4]  # Remove .sol extension
            if contract_name in src_files:
                # Find all JSON files in this directory
                contract_jsons = glob.glob(os.path.join(dir_path, "*.json"))
                json_files.extend(contract_jsons)
    
    return json_files

def load_ast_file(ast_file_path):
    """
    Load an AST file and return its contents.
    
    Args:
        ast_file_path (str): Path to the AST JSON file
        
    Returns:
        dict: The AST data as a dictionary
    """
    with open(ast_file_path, "r") as f:
        return json.load(f)