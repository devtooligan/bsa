"""
Debugging test for AST structure of emit statements.
"""

import os
import json
import pytest
from bsa.parser.ast_parser import ASTParser
from bsa.utils.forge import build_project_ast, find_source_files, find_ast_files, load_ast_file

def print_ast_file_paths(project_path):
    """Print all AST file paths."""
    # Find source and AST files
    source_files = find_source_files(project_path)
    ast_files = find_ast_files(project_path, list(source_files.keys()))
    
    print("\nAST files found:")
    for ast_file in ast_files:
        print(f"  {ast_file}")
    
    return ast_files

def test_emit_ast_structure():
    """Test that prints the AST structure of an emit statement for debugging."""
    # First run the parser to ensure we have AST files
    project_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "forgey2")
    
    # Print the forgey2/src/Counter.sol contents to verify it has the expected code
    counter_path = os.path.join(project_path, "src", "Counter.sol")
    print(f"\nReading Counter.sol at: {counter_path}")
    with open(counter_path, "r") as f:
        counter_code = f.read()
        print("\nCounter.sol contents:")
        print(counter_code)
    
    # Build the AST
    print("\nBuilding AST files...")
    build_project_ast(project_path)
    
    # Print and get AST file paths
    ast_files = print_ast_file_paths(project_path)
    
    print("\nAttempting to load AST files and find the Transfer function...")
    
    transfer_found = False
    
    # Try loading each AST file looking for the ERC20 contract
    for ast_file in ast_files:
        print(f"\nProcessing AST file: {ast_file}")
        ast_data = load_ast_file(ast_file)
        
        # Get all nodes
        ast_nodes = ast_data.get("ast", {}).get("nodes", [])
        print(f"Number of top-level nodes: {len(ast_nodes)}")
        
        # Find contract definition nodes
        for node in ast_nodes:
            if node.get("nodeType") == "ContractDefinition":
                print(f"Contract found: {node.get('name')}")
                
                # If this is the ERC20 contract, look for transfer function
                if node.get("name") == "ERC20":
                    contract_nodes = node.get("nodes", [])
                    print(f"Number of nodes in ERC20 contract: {len(contract_nodes)}")
                    
                    # Look through all nodes in the contract
                    for contract_node in contract_nodes:
                        if contract_node.get("nodeType") == "FunctionDefinition":
                            print(f"Function found: {contract_node.get('name')}")
                            
                            # If this is the transfer function, print details
                            if contract_node.get("name") == "transfer":
                                transfer_found = True
                                print("\nTransfer function found!")
                                body = contract_node.get("body", {})
                                statements = body.get("statements", [])
                                
                                print(f"Number of statements: {len(statements)}")
                                
                                # Print each statement
                                for i, stmt in enumerate(statements):
                                    print(f"\nStatement {i}, type: {stmt.get('nodeType')}")
                                    
                                    # Dump all statements to see their structure
                                    print(f"Statement {i} structure:")
                                    print(json.dumps(stmt, indent=2))
                                    
                                    # Special check for emit statements by looking at all function calls
                                    if stmt.get("nodeType") == "ExpressionStatement":
                                        expr = stmt.get("expression", {})
                                        if expr.get("nodeType") == "FunctionCall":
                                            # Check if this is an emit function call
                                            func_expr = expr.get("expression", {})
                                            if func_expr.get("nodeType") == "Identifier" and func_expr.get("name") == "emit":
                                                print("\nEmit statement found via Identifier name!")
                                            
                                            # Check expression type and sub-components
                                            print(f"\nExpression type: {func_expr.get('nodeType')}")
                                            if func_expr.get("nodeType") == "MemberAccess":
                                                print(f"Member name: {func_expr.get('memberName')}")
                                                base_expr = func_expr.get("expression", {})
                                                print(f"Base expression type: {base_expr.get('nodeType')}")
                                                if base_expr.get("nodeType") == "Identifier":
                                                    print(f"Base identifier name: {base_expr.get('name')}")
    
    if not transfer_found:
        print("\nNo transfer function found in any AST file! This is unexpected.")