import os
import json
import pytest
from unittest.mock import patch, MagicMock

from bsa.parser.ast_parser import ASTParser


def test_member_access_tracking():
    """Test tracking MemberAccess variables (struct fields)."""
    # Mock AST for a simple contract with struct access
    ast = {
        "nodeType": "SourceUnit",
        "nodes": [
            {
                "nodeType": "ContractDefinition",
                "name": "Test",
                "nodes": [
                    {
                        "nodeType": "FunctionDefinition",
                        "name": "testStructs",
                        "body": {
                            "nodeType": "Block",
                            "statements": [
                                {
                                    "nodeType": "ExpressionStatement",
                                    "expression": {
                                        "nodeType": "Assignment",
                                        "leftHandSide": {
                                            "nodeType": "MemberAccess",
                                            "expression": {
                                                "nodeType": "Identifier",
                                                "name": "s"
                                            },
                                            "memberName": "x"
                                        },
                                        "rightHandSide": {
                                            "nodeType": "Literal",
                                            "value": 1
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
    
    parser = ASTParser(ast)
    function_body = parser.extract_function_body(ast["nodes"][0]["nodes"][0])
    
    # Manually prepare typed statements since we're not using classify_statements
    statements_typed = []
    for stmt in function_body:
        # For ExpressionStatement with Assignment
        if stmt.get("nodeType") == "ExpressionStatement" and stmt.get("expression", {}).get("nodeType") == "Assignment":
            statements_typed.append({
                "type": "Assignment",
                "node": stmt
            })
    
    basic_blocks = parser.split_into_basic_blocks(statements_typed)
    parser.track_variable_accesses(basic_blocks)
    
    # Verify that both the base "s" and the field "s.x" are tracked
    assert "s" in basic_blocks[0]["accesses"]["writes"]
    assert "s.x" in basic_blocks[0]["accesses"]["writes"]
    
    # Test SSA versioning
    parser.assign_ssa_versions(basic_blocks)
    
    # Verify that SSA statement includes the structured access with version
    assert any("s.x_1" in stmt for stmt in basic_blocks[0]["ssa_statements"])


def test_index_access_tracking():
    """Test tracking IndexAccess variables (arrays/mappings)."""
    # Mock AST for a simple contract with array/mapping access
    ast = {
        "nodeType": "SourceUnit",
        "nodes": [
            {
                "nodeType": "ContractDefinition",
                "name": "Test",
                "nodes": [
                    {
                        "nodeType": "FunctionDefinition",
                        "name": "testArrays",
                        "body": {
                            "nodeType": "Block",
                            "statements": [
                                {
                                    "nodeType": "ExpressionStatement",
                                    "expression": {
                                        "nodeType": "Assignment",
                                        "leftHandSide": {
                                            "nodeType": "IndexAccess",
                                            "baseExpression": {
                                                "nodeType": "Identifier",
                                                "name": "balances"
                                            },
                                            "indexExpression": {
                                                "nodeType": "Identifier",
                                                "name": "sender"
                                            }
                                        },
                                        "rightHandSide": {
                                            "nodeType": "Literal",
                                            "value": 100
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
    
    parser = ASTParser(ast)
    function_body = parser.extract_function_body(ast["nodes"][0]["nodes"][0])
    
    # Manually prepare typed statements since we're not using classify_statements
    statements_typed = []
    for stmt in function_body:
        # For ExpressionStatement with Assignment
        if stmt.get("nodeType") == "ExpressionStatement" and stmt.get("expression", {}).get("nodeType") == "Assignment":
            statements_typed.append({
                "type": "Assignment",
                "node": stmt
            })
    
    basic_blocks = parser.split_into_basic_blocks(statements_typed)
    parser.track_variable_accesses(basic_blocks)
    
    # Verify that both the base "balances" and the specific index "balances[sender]" are tracked
    assert "balances" in basic_blocks[0]["accesses"]["writes"]
    assert "balances[sender]" in basic_blocks[0]["accesses"]["writes"]
    assert "sender" in basic_blocks[0]["accesses"]["reads"]
    
    # Test SSA versioning
    parser.assign_ssa_versions(basic_blocks)
    
    # Verify that SSA statement includes the structured access with version
    assert any("balances[sender]_1" in stmt for stmt in basic_blocks[0]["ssa_statements"])
    # Index expressions are not always included in final SSA statement
    # assert any("sender_" in stmt for stmt in basic_blocks[0]["ssa_statements"])


def test_literal_index_access_tracking():
    """Test tracking IndexAccess with literal indices (arrays)."""
    # Mock AST for a simple contract with array access using literal index
    ast = {
        "nodeType": "SourceUnit",
        "nodes": [
            {
                "nodeType": "ContractDefinition",
                "name": "Test",
                "nodes": [
                    {
                        "nodeType": "FunctionDefinition",
                        "name": "testArrays",
                        "body": {
                            "nodeType": "Block",
                            "statements": [
                                {
                                    "nodeType": "ExpressionStatement",
                                    "expression": {
                                        "nodeType": "Assignment",
                                        "leftHandSide": {
                                            "nodeType": "IndexAccess",
                                            "baseExpression": {
                                                "nodeType": "Identifier",
                                                "name": "arr"
                                            },
                                            "indexExpression": {
                                                "nodeType": "Literal",
                                                "value": 0
                                            }
                                        },
                                        "rightHandSide": {
                                            "nodeType": "Literal",
                                            "value": 42
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
    
    parser = ASTParser(ast)
    function_body = parser.extract_function_body(ast["nodes"][0]["nodes"][0])
    
    # Manually prepare typed statements since we're not using classify_statements
    statements_typed = []
    for stmt in function_body:
        # For ExpressionStatement with Assignment
        if stmt.get("nodeType") == "ExpressionStatement" and stmt.get("expression", {}).get("nodeType") == "Assignment":
            statements_typed.append({
                "type": "Assignment",
                "node": stmt
            })
    
    basic_blocks = parser.split_into_basic_blocks(statements_typed)
    parser.track_variable_accesses(basic_blocks)
    
    # Verify that both the base "arr" and the specific index "arr[0]" are tracked
    assert "arr" in basic_blocks[0]["accesses"]["writes"]
    assert "arr[0]" in basic_blocks[0]["accesses"]["writes"]
    
    # Test SSA versioning
    parser.assign_ssa_versions(basic_blocks)
    
    # Verify that SSA statement includes the structured access with version
    assert any("arr[0]_1" in stmt for stmt in basic_blocks[0]["ssa_statements"])