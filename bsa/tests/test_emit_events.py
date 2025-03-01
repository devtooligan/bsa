"""
Comprehensive tests for event emit detection and SSA representation.
"""

import os
import json
import pytest
from bsa.parser.ast_parser import ASTParser

class TestEmitEvents:
    """Test class for event emit functionality."""
    
    @classmethod
    def setup_class(cls):
        """Set up the test environment once for all tests in this class."""
        # Use the ERC20 example in forgey2 project
        cls.project_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "forgey2")
        parser = ASTParser(cls.project_path)
        cls.data = parser.parse()
        
        # Find the ERC20 contract
        cls.erc20_contract = next((contract for contract in cls.data if contract["contract"]["name"] == "ERC20"), None)
        assert cls.erc20_contract is not None, "ERC20 contract not found"
        
        # Get the transfer function
        cls.transfer = next((e for e in cls.erc20_contract["entrypoints"] if e["name"] == "transfer"), None)
        assert cls.transfer is not None, "transfer function not found"
        
        # Find the emit block for reuse in tests
        cls.emit_block = None
        cls.emit_statement = None
        for block in cls.transfer["ssa"]:
            for stmt in block["ssa_statements"]:
                if "emit Transfer" in stmt:
                    cls.emit_block = block
                    cls.emit_statement = stmt
                    break
            if cls.emit_block:
                break
                
        assert cls.emit_block is not None, "Emit block not found in setup"
        assert cls.emit_statement is not None, "Emit statement not found in setup"
    
    def test_emit_inclusion(self):
        """Test that emit events are included in the SSA output."""
        # Verify the emit statement pattern
        expected_pattern = "emit Transfer(msg.sender_0, recipient_0, amount_0)"
        assert expected_pattern in self.emit_statement, f"Expected emit pattern '{expected_pattern}' not found"
    
    def test_emit_block_splitting(self):
        """Test that emit statements cause blocks to be split correctly."""
        # The transfer function should have at least 4 blocks due to splitting:
        # 1. First block with the balanceOf[msg.sender] -= amount
        # 2. Second block with the balanceOf[recipient] += amount
        # 3. Third block with the emit Transfer statement
        # 4. Fourth block with the return statement
        assert len(self.transfer["ssa"]) >= 4, f"Expected at least 4 blocks, but got {len(self.transfer['ssa'])}"
        
        # Verify the emit block has the correct terminator
        assert self.emit_block["terminator"] == "EmitStatement", \
            f"Expected terminator 'EmitStatement', but got {self.emit_block.get('terminator')}"
    
    def test_emit_accesses(self):
        """Test that emit statements correctly track variable accesses."""
        # Verify the block's accesses include the variables used in the emit statement
        reads = set(self.emit_block["accesses"]["reads"])
        # Should include msg.sender, recipient, and amount as reads
        expected_reads = {"msg.sender", "recipient", "amount"}
        
        # Check if each expected read is in the actual reads list
        for expected in expected_reads:
            assert expected in reads, f"Expected '{expected}' in reads, but not found"
    
    def test_emit_ast_structure(self):
        """Test that EmitStatement nodes are correctly identified in the AST."""
        # Check the raw body statements for EmitStatement
        emit_stmt_found = False
        for stmt in self.transfer.get("body_raw", []):
            if stmt.get("nodeType") == "EmitStatement":
                emit_stmt_found = True
                break
        
        assert emit_stmt_found, "No EmitStatement found in function body raw statements"
        
        # Verify emit format in the SSA output
        assert self.emit_statement.startswith("emit Transfer("), \
            f"Emit statement should start with 'emit Transfer(', got: {self.emit_statement}"
            
        # Verify proper argument formatting with commas
        args_part = self.emit_statement[len("emit Transfer("):-1]  # Remove "emit Transfer(" and ")"
        args = [arg.strip() for arg in args_part.split(",")]
        assert len(args) == 3, f"Expected 3 args in emit statement, got {len(args)}: {args}"