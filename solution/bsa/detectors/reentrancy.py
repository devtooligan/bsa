"""
Reentrancy vulnerability detector for BSA.
"""

from bsa.detectors.base import Detector

class ReentrancyDetector(Detector):
    """
    Detector for reentrancy vulnerabilities in Solidity contracts.
    
    This detector finds instances where a contract makes an external call 
    followed by a state variable write, which is a pattern vulnerable to reentrancy attacks.
    In a reentrancy attack, the external call can trigger a callback to the original contract,
    potentially allowing an attacker to execute code before state updates are completed.
    """
    
    def __init__(self):
        """Initialize the reentrancy detector."""
        super().__init__(name="Reentrancy")
        self.findings = []
    
    def detect(self, contract_data):
        """
        Run the reentrancy detection algorithm on contract data.
        
        Args:
            contract_data (dict): Contract data for analysis
            
        Returns:
            list: List of findings
        """
        # Reset findings
        self.findings = []
        
        # Extract contract and entrypoints
        contract = contract_data.get("contract", {})
        entrypoints = contract_data.get("entrypoints", [])
        state_vars = contract.get("state_vars", [])
        contract_name = contract.get("name", "Unknown")
        
        # Debug information - commented out for clarity in output
        # print(f"DEBUG detect: Contract: {contract_name}")
        # print(f"DEBUG detect: State vars: {[v.get('name') for v in state_vars]}")
        
        # Analyze each entrypoint for reentrancy
        for entrypoint in entrypoints:
            function_name = entrypoint.get("name", "Unknown")
            
            # Get the function body - always prefer basic blocks over raw body
            if "basic_blocks" in entrypoint:
                body = entrypoint  # Pass the entire entrypoint for basic blocks access
                # print(f"DEBUG detect: Using basic blocks")
            else:
                body = {"statements": entrypoint.get("body_raw", [])}
                # print(f"DEBUG detect: Using raw body")
            
            # Check for reentrancy
            reentrancy_result = self.check_reentrancy(body, state_vars)
            
            if reentrancy_result:
                # If the result is a string, it contains details about the vulnerable statement
                if isinstance(reentrancy_result, str):
                    self.add_finding({
                        "contract_name": contract_name,
                        "function_name": function_name,
                        "description": f"External call detected before state variable write ({reentrancy_result})",
                        "severity": "High"
                    })
                else:
                    # Backward compatibility for when the result is just True
                    self.add_finding({
                        "contract_name": contract_name,
                        "function_name": function_name,
                        "description": "External call detected before state variable write",
                        "severity": "High"
                    })
        
        return self.findings
    
    def is_external_call(self, node):
        """
        Check if a node represents an external call like contract.call() or address.transfer().
        
        Args:
            node (dict): AST node to check
            
        Returns:
            bool: True if the node represents an external call, False otherwise
        """
        # For Variable Declaration Statements that contain a call
        if node.get("nodeType") == "VariableDeclarationStatement":
            initialValue = node.get("initialValue", {})
            if initialValue:
                return self.is_external_call(initialValue)
        
        # If this is an expression statement, get the expression
        if node.get("nodeType") == "ExpressionStatement":
            node = node.get("expression", {})
        
        if node.get("nodeType") != "FunctionCall":
            return False
        
        expression = node.get("expression", {})
        expr_type = expression.get("nodeType", "unknown")
        
        # Check for function call options (like .call{value: x}(""))
        if expr_type == "FunctionCallOptions":
            base_expr = expression.get("expression", {})
            if base_expr.get("nodeType") == "MemberAccess":
                member_name = base_expr.get("memberName", "")
                external_call_names = ["call", "delegatecall", "staticcall", "transfer", "send"]
                return member_name in external_call_names
        
        # Check for common external call patterns
        if expr_type == "MemberAccess":
            member_name = expression.get("memberName", "")
            # Common external call functions
            external_call_names = ["call", "delegatecall", "staticcall", "transfer", "send"]
            return member_name in external_call_names
        
        return False
    
    def is_state_variable_write(self, node, state_vars):
        """
        Check if a node represents a state variable write operation.
        
        Args:
            node (dict): AST node to check
            state_vars (list): List of state variables
            
        Returns:
            bool: True if the node represents a state variable write, False otherwise
        """
        # If this is an expression statement, get the expression
        if node.get("nodeType") == "ExpressionStatement":
            node = node.get("expression", {})
        
        if node.get("nodeType") != "Assignment":
            return False
        
        left_hand_side = node.get("leftHandSide", {})
        
        # Check for direct state variable assignment (variable name)
        if left_hand_side.get("nodeType") == "Identifier":
            var_name = left_hand_side.get("name", "")
            # Check if this name is in our state variables
            return var_name in [var["name"] for var in state_vars]
        
        # Check for mapping or array access in state variables (e.g., balances[msg.sender] = 0)
        if left_hand_side.get("nodeType") == "IndexAccess":
            base_expr = left_hand_side.get("baseExpression", {})
            if base_expr.get("nodeType") == "Identifier":
                var_name = base_expr.get("name", "")
                return var_name in [var["name"] for var in state_vars]
        
        return False
    
    def check_reentrancy(self, body, state_vars):
        """
        Check a function body for reentrancy vulnerabilities.
        
        Args:
            body (dict): Function body AST node or basic blocks data
            state_vars (list): List of state variables
            
        Returns:
            bool: True if reentrancy is detected (external call before state var write)
        """
        # Check if this is basic blocks format (from SSA transformation)
        if isinstance(body, dict) and "basic_blocks" in body:
            return self._check_reentrancy_in_blocks(body["basic_blocks"], state_vars)
            
        # Original AST node processing
        statements = body.get("statements", [])
        has_external_call = False
        
        # Flatten statements to make it easier to process
        flat_statements = []
        for statement in statements:
            flat_statements.append(statement)
            # Also check for blocks and their statements
            if statement.get("nodeType") == "Block":
                flat_statements.extend(statement.get("statements", []))
        
        # Process statements in order
        for i, statement in enumerate(flat_statements):
            # If we've seen an external call, check if this statement writes to state
            if has_external_call and self.is_state_variable_write(statement, state_vars):
                # For raw AST, we can't provide detailed SSA information
                # Just report the statement index for reference
                return f"state write at statement {i}"
                
            # Check for external calls
            if self.is_external_call(statement):
                has_external_call = True
        
        return False
        
    def _check_reentrancy_in_blocks(self, basic_blocks, state_vars):
        """
        Check for reentrancy in SSA basic blocks format.
        
        Args:
            basic_blocks (list): List of basic block dictionaries
            state_vars (list): List of state variables
            
        Returns:
            bool: True if reentrancy is detected
        """
        # With the new block splitting, external calls and state writes will be in separate blocks
        # First, we need to find blocks that have external calls
        call_blocks = []
        state_write_blocks = []
        
        # Identify blocks with calls and blocks with state writes
        for i, block in enumerate(basic_blocks):
            # Get all SSA statements in this block
            statements = block.get("ssa_statements", [])
            
            has_external_call = False
            has_state_write = False
            
            # First check for revert statements (which are not external calls)
            has_revert_statement = False
            for stmt in statements:
                if stmt.startswith("revert ") or stmt.startswith("require ") or stmt.startswith("assert "):
                    has_revert_statement = True
                    break
                    
            # If no revert statements, check for external calls
            if not has_revert_statement:
                for stmt in statements:
                    # Only consider call type statements
                    if "call[" in stmt and "(" in stmt and ")" in stmt:
                        # Parse the call parts: type and function name
                        call_type = stmt.split("call[")[1].split("]")[0]
                        
                        # Extract function name
                        func_call_part = stmt.split("]")[1].strip()
                        if func_call_part.startswith("(") and func_call_part.endswith(")"):
                            func_and_args = func_call_part[1:-1]  # Remove outer parentheses
                            
                            # Get function name
                            if "," in func_and_args:
                                func_name = func_and_args.split(",", 1)[0].strip()
                            else:
                                func_name = func_and_args.strip()
                            
                            # Check if this is an actual external call (not a revert type)
                            is_external = False
                            
                            # Check call type first
                            if call_type in ["external", "low_level_external", "delegatecall", "staticcall"]:
                                # Only consider it external if it's not a revert-like function
                                if func_name not in ["revert", "require", "assert"]:
                                    is_external = True
                            
                            if is_external:
                                has_external_call = True
                                break
            
            # Check for state variable writes
            for stmt in statements:
                for state_var in state_vars:
                    var_name = state_var["name"]
                    # Check for pattern like "x_1 = " which represents writing to state var x
                    if f"{var_name}_" in stmt and " = " in stmt:
                        has_state_write = True
                        break
                if has_state_write:
                    break
            
            # Record the results
            if has_external_call:
                call_blocks.append(i)
            if has_state_write:
                state_write_blocks.append(i)
        
        # Now check if any state write block comes after a call block
        # (blocks are ordered sequentially due to our splitting)
        for call_block_idx in call_blocks:
            for write_block_idx in state_write_blocks:
                if write_block_idx > call_block_idx:
                    # Get the vulnerable statement details
                    write_block = basic_blocks[write_block_idx]
                    write_block_id = write_block.get("id", "Unknown")
                    
                    # Find the statement that writes to a state variable
                    vuln_statement = None
                    for stmt in write_block.get("ssa_statements", []):
                        for state_var in state_vars:
                            var_name = state_var["name"]
                            if f"{var_name}_" in stmt and " = " in stmt:
                                vuln_statement = stmt
                                break
                        if vuln_statement:
                            break
                    
                    # Return details about the vulnerable state write
                    write_details = f"{vuln_statement} at {write_block_id}" if vuln_statement else f"state write at {write_block_id}"
                    return write_details
        
        return False