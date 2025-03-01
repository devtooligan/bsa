"""
Debug tests for event emit parsing in BSA.
"""

import os
import json
import pytest
from bsa.parser.ast_parser import ASTParser

def test_debug_transfer_function():
    """Print the full details of the transfer function in ERC20."""
    # Use the ERC20 example in forgey2 project
    project_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "forgey2")
    parser = ASTParser(project_path)
    data = parser.parse()
    
    # Find the ERC20 contract
    erc20_contract = next((contract for contract in data if contract["contract"]["name"] == "ERC20"), None)
    assert erc20_contract is not None, "ERC20 contract not found"
    
    # Get the transfer function
    transfer = next((e for e in erc20_contract["entrypoints"] if e["name"] == "transfer"), None)
    assert transfer is not None, "transfer function not found"
    
    # Print full details
    print("\nTransfer function raw body statements:")
    for i, stmt in enumerate(transfer.get("body_raw", [])):
        print(f"\nStatement {i}, type: {stmt.get('nodeType')}")
        # Look for EmitStatement
        if stmt.get("nodeType") == "EmitStatement":
            print("Found EmitStatement in raw body!")
    
    # Print the basic blocks structure
    print("\nBasic blocks before SSA:")
    for i, block in enumerate(transfer.get("basic_blocks", [])):
        print(f"\nBlock {i}, ID: {block.get('id')}")
        print(f"Terminator: {block.get('terminator')}")
        print(f"Statements count: {len(block.get('statements', []))}")
        for j, stmt in enumerate(block.get("statements", [])):
            print(f"  Statement {j}, type: {stmt.get('type')}")
            # Look for EmitStatement type
            if stmt.get("type") == "EmitStatement":
                print("  Found EmitStatement in basic blocks!")
    
    # Print the final SSA output
    print("\nSSA blocks:")
    for i, block in enumerate(transfer.get("ssa", [])):
        print(f"\nBlock {i}, ID: {block.get('id')}")
        print(f"Terminator: {block.get('terminator')}")
        print(f"SSA statements:")
        for j, stmt in enumerate(block.get("ssa_statements", [])):
            print(f"  {j}: {stmt}")
        print(f"Accesses reads: {block.get('accesses', {}).get('reads', [])}")
        print(f"Accesses writes: {block.get('accesses', {}).get('writes', [])}")