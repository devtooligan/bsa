"""
Test event emit detection and SSA representation.
"""

import os
import pytest
from bsa.parser.ast_parser import ASTParser

class TestEmitEvents:
    """Test class for event emit functionality."""
    
    def test_emit_inclusion(self):
        """Test that emit events are included in the SSA output."""
        # Use the ERC20 example in forgey2 project
        parser = ASTParser(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "forgey2"))
        data = parser.parse()
        
        # Find the ERC20 contract
        erc20_contract = next((contract for contract in data if contract["contract"]["name"] == "ERC20"), None)
        assert erc20_contract is not None, "ERC20 contract not found"
        
        # Get the transfer function
        transfer = next((e for e in erc20_contract["entrypoints"] if e["name"] == "transfer"), None)
        assert transfer is not None, "transfer function not found"
        
        # Check if the emit Transfer statement is included in the SSA
        emit_statements = []
        for block in transfer["ssa"]:
            for stmt in block["ssa_statements"]:
                if "emit Transfer" in stmt:
                    emit_statements.append(stmt)
        
        assert len(emit_statements) > 0, "No emit Transfer statements found"
        expected_pattern = "emit Transfer(msg.sender_0, recipient_0, amount_0)"
        assert any(expected_pattern in stmt for stmt in emit_statements), f"Expected emit pattern '{expected_pattern}' not found"
    
    def test_emit_block_splitting(self):
        """Test that emit statements cause blocks to be split correctly."""
        # Use the ERC20 example in forgey2 project
        parser = ASTParser(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "forgey2"))
        data = parser.parse()
        
        # Find the ERC20 contract
        erc20_contract = next((contract for contract in data if contract["contract"]["name"] == "ERC20"), None)
        assert erc20_contract is not None, "ERC20 contract not found"
        
        # Get the transfer function
        transfer = next((e for e in erc20_contract["entrypoints"] if e["name"] == "transfer"), None)
        assert transfer is not None, "transfer function not found"
        
        # The transfer function should have at least 4 blocks due to splitting:
        # 1. First block with the balanceOf[msg.sender] -= amount
        # 2. Second block with the balanceOf[recipient] += amount
        # 3. Third block with the emit Transfer statement
        # 4. Fourth block with the return statement
        assert len(transfer["ssa"]) >= 4, f"Expected at least 4 blocks, but got {len(transfer['ssa'])}"
        
        # Find the block with the emit statement
        emit_block = None
        for block in transfer["ssa"]:
            for stmt in block["ssa_statements"]:
                if "emit Transfer" in stmt:
                    emit_block = block
                    break
            if emit_block:
                break
        
        assert emit_block is not None, "Block with emit statement not found"
        assert emit_block["terminator"] == "EmitStatement", f"Expected terminator 'EmitStatement', but got {emit_block.get('terminator')}"
    
    def test_emit_accesses(self):
        """Test that emit statements correctly track variable accesses."""
        # Use the ERC20 example in forgey2 project
        parser = ASTParser(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "forgey2"))
        data = parser.parse()
        
        # Find the ERC20 contract
        erc20_contract = next((contract for contract in data if contract["contract"]["name"] == "ERC20"), None)
        assert erc20_contract is not None, "ERC20 contract not found"
        
        # Get the transfer function
        transfer = next((e for e in erc20_contract["entrypoints"] if e["name"] == "transfer"), None)
        assert transfer is not None, "transfer function not found"
        
        # Find the block with the emit statement
        emit_block = None
        for block in transfer["ssa"]:
            for stmt in block["ssa_statements"]:
                if "emit Transfer" in stmt:
                    emit_block = block
                    break
            if emit_block:
                break
        
        assert emit_block is not None, "Block with emit statement not found"
        
        # Verify the block's accesses include the variables used in the emit statement
        reads = set(emit_block["accesses"]["reads"])
        # Should include msg.sender, recipient, and amount as reads
        expected_reads = {"msg.sender", "recipient", "amount"}
        
        # Check if each expected read is in the actual reads list
        for expected in expected_reads:
            assert expected in reads, f"Expected '{expected}' in reads, but not found"