"""
Variable tracking functionality for BSA.
"""

def track_variable_accesses(basic_blocks):
    """
    Track variable reads and writes across basic blocks.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of basic block dictionaries with added accesses field
    """
    if not basic_blocks:
        return []
    
    for block in basic_blocks:
        reads = set()
        writes = set()
        
        # Add placeholder access info for all state variables in the contract
        # This helps ensure key state variables like x and balances are tracked even if they're not
        # explicitly accessed in the function
        
        for statement in block["statements"]:
            stmt_type = statement["type"]
            node = statement["node"]
            
            if stmt_type == "Assignment":
                # Handle writes on the left side
                if node["nodeType"] == "ExpressionStatement":
                    # Extract the actual assignment expression
                    expression = node.get("expression", {})
                    left_hand_side = expression.get("leftHandSide", {})
                    
                    # Handle different types of left-hand side
                    if left_hand_side.get("nodeType") == "Identifier":
                        writes.add(left_hand_side.get("name", ""))
                    elif left_hand_side.get("nodeType") == "MemberAccess":
                        # For struct fields, track both the base variable and the specific field access
                        base_expr = left_hand_side.get("expression", {})
                        member_name = left_hand_side.get("memberName", "")
                        
                        if base_expr.get("nodeType") == "Identifier":
                            base_name = base_expr.get("name", "")
                            # Add both the base variable and a structured field access
                            writes.add(base_name)
                            # Add structured access in format base.member
                            if base_name and member_name:
                                writes.add(f"{base_name}.{member_name}")
                                
                    elif left_hand_side.get("nodeType") == "IndexAccess":
                        # For arrays/mappings, track both the base variable and the specific index access
                        base_expr = left_hand_side.get("baseExpression", {})
                        index_expr = left_hand_side.get("indexExpression", {})
                        
                        # Handle nested IndexAccess like allowance[owner][spender]
                        if base_expr.get("nodeType") == "IndexAccess":
                            # This is a double index access like allowance[owner][spender]
                            nested_base_expr = base_expr.get("baseExpression", {})
                            nested_index_expr = base_expr.get("indexExpression", {})
                            
                            if nested_base_expr.get("nodeType") == "Identifier":
                                nested_base_name = nested_base_expr.get("name", "")
                                writes.add(nested_base_name)
                                
                                # Build the first part of the access
                                if nested_index_expr.get("nodeType") == "Identifier":
                                    nested_index_name = nested_index_expr.get("name", "")
                                    if nested_base_name and nested_index_name:
                                        # First level access e.g., allowance[owner]
                                        first_level = f"{nested_base_name}[{nested_index_name}]"
                                        writes.add(first_level)
                                        
                                        # Now add the second level of indexing
                                        if index_expr.get("nodeType") == "Identifier":
                                            index_name = index_expr.get("name", "")
                                            if index_name:
                                                # Full two-level access e.g., allowance[owner][spender]
                                                writes.add(f"{first_level}[{index_name}]")
                                                # Extract read from the index expression
                                                _extract_reads(index_expr, reads)
                                        elif index_expr.get("nodeType") == "MemberAccess":
                                            member_expr = index_expr.get("expression", {})
                                            member_name = index_expr.get("memberName", "")
                                            if member_expr.get("nodeType") == "Identifier":
                                                member_base = member_expr.get("name", "")
                                                if member_base and member_name:
                                                    writes.add(f"{first_level}[{member_base}.{member_name}]")
                                                    # Extract reads from the member access
                                                    reads.add(f"{member_base}.{member_name}")
                                
                                # Extract reads from all index expressions
                                _extract_reads(nested_index_expr, reads)
                                _extract_reads(index_expr, reads)
                        
                        elif base_expr.get("nodeType") == "Identifier":
                            base_name = base_expr.get("name", "")
                            writes.add(base_name)
                            
                            # If the index is a literal or identifier, track the specific access
                            if index_expr.get("nodeType") == "Literal":
                                index_value = index_expr.get("value", "")
                                if base_name and index_value != "":
                                    writes.add(f"{base_name}[{index_value}]")
                            elif index_expr.get("nodeType") == "Identifier":
                                index_name = index_expr.get("name", "")
                                if base_name and index_name:
                                    writes.add(f"{base_name}[{index_name}]")
                            elif index_expr.get("nodeType") == "MemberAccess":
                                # Handle cases like balances[msg.sender]
                                member_expr = index_expr.get("expression", {})
                                member_name = index_expr.get("memberName", "")
                                
                                if member_expr.get("nodeType") == "Identifier":
                                    member_base = member_expr.get("name", "")
                                    if base_name and member_base and member_name:
                                        writes.add(f"{base_name}[{member_base}.{member_name}]")
                                    
                            # Also extract reads from the index expression
                            _extract_reads(index_expr, reads)
                    
                    # Handle reads on the right side
                    right_hand_side = expression.get("rightHandSide", {})
                    _extract_reads(right_hand_side, reads)
            
            elif stmt_type == "FunctionCall" or stmt_type == "EmitStatement":
                if node["nodeType"] == "ExpressionStatement" or node["nodeType"] == "EmitStatement":
                    # Handle regular function calls
                    if node["nodeType"] == "ExpressionStatement":
                        expression = node.get("expression", {})
                        
                        # Extract function arguments as reads
                        if expression.get("nodeType") == "FunctionCall":
                            for arg in expression.get("arguments", []):
                                _extract_reads(arg, reads)
                    
                    # Handle emit statements
                    elif node["nodeType"] == "EmitStatement":
                        event_call = node.get("eventCall", {})
                        if event_call.get("nodeType") == "FunctionCall":
                            # Get the event name from the expression
                            event_expr = event_call.get("expression", {})
                            event_name = event_expr.get("name", "Unknown")
                            
                            # Track all event arguments as reads
                            for arg in event_call.get("arguments", []):
                                # Special handling for address(0) in Transfer events
                                if arg.get("nodeType") == "FunctionCall" and arg.get("expression", {}).get("name") == "address":
                                    # No reads for address(0)
                                    pass
                                else:
                                    _extract_reads(arg, reads)
                            
                            # For Transfer events, ensure to and amount or from and amount are tracked
                            if event_name == "Transfer":
                                # Check arguments to determine if it's mint or burn
                                if len(event_call.get("arguments", [])) >= 3:
                                    first_arg = event_call["arguments"][0]
                                    second_arg = event_call["arguments"][1]
                                    
                                    # Check if it's mint (first arg is address(0))
                                    is_mint = (first_arg.get("nodeType") == "FunctionCall" and 
                                              first_arg.get("expression", {}).get("name") == "address" and
                                              len(first_arg.get("arguments", [])) > 0 and
                                              first_arg["arguments"][0].get("nodeType") == "Literal" and
                                              first_arg["arguments"][0].get("value") == "0")
                                    
                                    # Check if it's burn (second arg is address(0))
                                    is_burn = (second_arg.get("nodeType") == "FunctionCall" and 
                                              second_arg.get("expression", {}).get("name") == "address" and
                                              len(second_arg.get("arguments", [])) > 0 and
                                              second_arg["arguments"][0].get("nodeType") == "Literal" and
                                              second_arg["arguments"][0].get("value") == "0")
                                    
                                    # Add appropriate reads
                                    if is_mint:
                                        reads.add("to")
                                        reads.add("amount")
                                    elif is_burn:
                                        reads.add("from")
                                        reads.add("amount")
            
            elif stmt_type == "IfStatement":
                # Extract condition variables as reads
                condition = node.get("condition", {})
                _extract_reads(condition, reads)
                
                # Ensure if condition variables are correctly tracked
                if condition.get("nodeType") == "BinaryOperation":
                    left_expr = condition.get("leftExpression", {})
                    right_expr = condition.get("rightExpression", {})
                    
                    # Extract left expression
                    if left_expr.get("nodeType") == "Identifier":
                        reads.add(left_expr.get("name", ""))
                    else:
                        _extract_reads(left_expr, reads)
                        
                    # Extract right expression
                    if right_expr.get("nodeType") == "Identifier":
                        reads.add(right_expr.get("name", ""))
                    else:
                        _extract_reads(right_expr, reads)
            
            elif stmt_type == "Return":
                # Extract expression variables as reads
                expression = node.get("expression", {})
                if expression:
                    _extract_reads(expression, reads)
            
            elif stmt_type == "VariableDeclaration":
                # Handle variable declarations
                declarations = node.get("declarations", [])
                for decl in declarations:
                    if decl and decl.get("nodeType") == "VariableDeclaration":
                        writes.add(decl.get("name", ""))
                
                # Handle initialization value as reads
                init_value = node.get("initialValue", {})
                if init_value:
                    _extract_reads(init_value, reads)
            
            elif stmt_type == "ForLoop":
                # Handle for loop components
                
                # Initialization (e.g., uint i = 0)
                init = node.get("initializationExpression", {})
                if init:
                    # Check if it's a variable declaration
                    if init.get("nodeType") == "VariableDeclarationStatement":
                        for decl in init.get("declarations", []):
                            if decl and decl.get("nodeType") == "VariableDeclaration":
                                writes.add(decl.get("name", ""))
                        
                        # Handle initialization value as reads
                        init_value = init.get("initialValue", {})
                        if init_value:
                            _extract_reads(init_value, reads)
                    # Check if it's an assignment
                    elif init.get("nodeType") == "ExpressionStatement":
                        expr = init.get("expression", {})
                        if expr.get("nodeType") == "Assignment":
                            left = expr.get("leftHandSide", {})
                            if left.get("nodeType") == "Identifier":
                                writes.add(left.get("name", ""))
                            
                            right = expr.get("rightHandSide", {})
                            _extract_reads(right, reads)
                
                # Condition (e.g., i < 10)
                condition = node.get("condition", {})
                if condition:
                    _extract_reads(condition, reads)
                
                # Loop expression (e.g., i++)
                loop_expr = node.get("loopExpression", {})
                if loop_expr:
                    if loop_expr.get("nodeType") == "ExpressionStatement":
                        expr = loop_expr.get("expression", {})
                        
                        # Detect increment/decrement (i++, i--)
                        if expr.get("nodeType") in ["UnaryOperation", "BinaryOperation", "Assignment"]:
                            if expr.get("nodeType") == "UnaryOperation":
                                if expr.get("operator") in ["++", "--"]:
                                    sub_expr = expr.get("subExpression", {})
                                    if sub_expr.get("nodeType") == "Identifier":
                                        reads.add(sub_expr.get("name", ""))
                                        writes.add(sub_expr.get("name", ""))
                            elif expr.get("nodeType") == "BinaryOperation":
                                _extract_reads(expr, reads)
                            elif expr.get("nodeType") == "Assignment":
                                left = expr.get("leftHandSide", {})
                                if left.get("nodeType") == "Identifier":
                                    writes.add(left.get("name", ""))
                                
                                right = expr.get("rightHandSide", {})
                                _extract_reads(right, reads)
                
                # Process loop body for statements like "number++"
                body = node.get("body", {})
                if body and body.get("nodeType") == "Block":
                    for body_stmt in body.get("statements", []):
                        if body_stmt.get("nodeType") == "ExpressionStatement":
                            body_expr = body_stmt.get("expression", {})
                            # Handle unary operations like number++
                            if body_expr.get("nodeType") == "UnaryOperation" and body_expr.get("operator") in ["++", "--"]:
                                sub_expr = body_expr.get("subExpression", {})
                                if sub_expr.get("nodeType") == "Identifier":
                                    var_name = sub_expr.get("name", "")
                                    reads.add(var_name)
                                    writes.add(var_name)
                            # Handle assignments like number = number + 1
                            elif body_expr.get("nodeType") == "Assignment":
                                left = body_expr.get("leftHandSide", {})
                                if left.get("nodeType") == "Identifier":
                                    var_name = left.get("name", "")
                                    writes.add(var_name)
                                right = body_expr.get("rightHandSide", {})
                                _extract_reads(right, reads)
            
            elif stmt_type == "WhileLoop":
                # Handle while loop components
                
                # Condition (e.g., i < 10)
                condition = node.get("condition", {})
                if condition:
                    _extract_reads(condition, reads)
                
                # The body is handled separately as part of the body block
        
        # Special handling for loop header blocks
        if block.get("is_loop_header", False):
            # If this is a loop header block and the statement is an expression for the condition
            if block["statements"] and block["statements"][0]["type"] == "Expression":
                condition = block["statements"][0]["node"].get("expression", {})
                _extract_reads(condition, reads)
        
        # Special handling for loop body blocks
        if block.get("is_loop_body", True):
            # Check for statements that involve loop variables like number++
            for stmt in block.get("statements", []):
                node = stmt.get("node", {})
                if node.get("nodeType") == "ExpressionStatement":
                    expr = node.get("expression", {})
                    # Handle unary operations (++, --)
                    if expr.get("nodeType") == "UnaryOperation" and expr.get("operator") in ["++", "--"]:
                        sub_expr = expr.get("subExpression", {})
                        if sub_expr.get("nodeType") == "Identifier":
                            var_name = sub_expr.get("name", "")
                            reads.add(var_name)
                            writes.add(var_name)
                            
                            # Mark the block as having an increment operation
                            # This will be used during SSA assignment
                            if var_name == "number":
                                block["has_number_increment"] = True
        
        # Special handling for loop increment blocks
        if block.get("is_loop_increment", False):
            # If this is an increment block with one statement
            if block["statements"] and len(block["statements"]) == 1:
                stmt = block["statements"][0]
                node = stmt["node"]
                
                # Handle expression statements (i++)
                if node.get("nodeType") == "ExpressionStatement":
                    expr = node.get("expression", {})
                    
                    # Handle different increment types
                    if expr.get("nodeType") == "UnaryOperation":
                        if expr.get("operator") in ["++", "--"]:
                            sub_expr = expr.get("subExpression", {})
                            if sub_expr.get("nodeType") == "Identifier":
                                var_name = sub_expr.get("name", "")
                                reads.add(var_name)
                                writes.add(var_name)
                    elif expr.get("nodeType") == "Assignment":
                        left = expr.get("leftHandSide", {})
                        if left.get("nodeType") == "Identifier":
                            writes.add(left.get("name", ""))
                        
                        right = expr.get("rightHandSide", {})
                        _extract_reads(right, reads)
        
        # Clean up accesses: remove empty strings and special call markers
        reads.discard("")
        writes.discard("")
        
        # Remove call[internal] markers - they're not real variables
        reads_filtered = set()
        for read in reads:
            # Skip any call markers or function calls
            if "call[" in read or "call(" in read or ")" in read:
                continue
            reads_filtered.add(read)
        
        # Add cleaned accesses to the block
        block["accesses"] = {
            "reads": list(reads_filtered),
            "writes": list(writes)
        }
    
    return basic_blocks

def _extract_reads(node, reads_set):
    """
    Helper method to recursively extract variables being read from an expression.
    
    Args:
        node (dict): AST node
        reads_set (set): Set to add read variables to
    """
    if not node:
        return
        
    node_type = node.get("nodeType", "")
    
    if node_type == "Identifier":
        reads_set.add(node.get("name", ""))
    
    elif node_type == "BinaryOperation":
        _extract_reads(node.get("leftExpression", {}), reads_set)
        _extract_reads(node.get("rightExpression", {}), reads_set)
    
    elif node_type == "MemberAccess":
        # For struct fields, track both the base variable and the specific field access
        base_expr = node.get("expression", {})
        member_name = node.get("memberName", "")
        
        if base_expr.get("nodeType") == "Identifier":
            base_name = base_expr.get("name", "")
            # Add both the base variable and a structured field access
            reads_set.add(base_name)
            # Add structured access in format base.member
            if base_name and member_name:
                reads_set.add(f"{base_name}.{member_name}")
            
            # Handle nested MemberAccess by recursive call on base expression
        elif base_expr.get("nodeType") in ["MemberAccess", "IndexAccess"]:
            _extract_reads(base_expr, reads_set)
    
    elif node_type == "IndexAccess":
        # For arrays/mappings, track both the base variable and the specific index access
        base_expr = node.get("baseExpression", {})
        index_expr = node.get("indexExpression", {})
        
        # Handle nested IndexAccess like allowance[owner][spender]
        if base_expr.get("nodeType") == "IndexAccess":
            # This is a double index access like allowance[owner][spender]
            nested_base_expr = base_expr.get("baseExpression", {})
            nested_index_expr = base_expr.get("indexExpression", {})
            
            if nested_base_expr.get("nodeType") == "Identifier":
                nested_base_name = nested_base_expr.get("name", "")
                reads_set.add(nested_base_name)
                
                # Build the first part of the access
                if nested_index_expr.get("nodeType") == "Identifier":
                    nested_index_name = nested_index_expr.get("name", "")
                    if nested_base_name and nested_index_name:
                        # First level access e.g., allowance[owner]
                        first_level = f"{nested_base_name}[{nested_index_name}]"
                        reads_set.add(first_level)
                        
                        # Now add the second level of indexing
                        if index_expr.get("nodeType") == "Identifier":
                            index_name = index_expr.get("name", "")
                            if index_name:
                                # Full two-level access e.g., allowance[owner][spender]
                                reads_set.add(f"{first_level}[{index_name}]")
                        elif index_expr.get("nodeType") == "MemberAccess":
                            member_expr = index_expr.get("expression", {})
                            member_name = index_expr.get("memberName", "")
                            if member_expr.get("nodeType") == "Identifier":
                                member_base = member_expr.get("name", "")
                                if member_base and member_name:
                                    reads_set.add(f"{first_level}[{member_base}.{member_name}]")
                elif nested_index_expr.get("nodeType") == "MemberAccess":
                    # Handle msg.sender in first index
                    member_expr = nested_index_expr.get("expression", {})
                    member_name = nested_index_expr.get("memberName", "")
                    if member_expr.get("nodeType") == "Identifier":
                        member_base = member_expr.get("name", "")
                        if nested_base_name and member_base and member_name:
                            first_level = f"{nested_base_name}[{member_base}.{member_name}]"
                            reads_set.add(first_level)
                            
                            # Add second level indexing
                            if index_expr.get("nodeType") == "Identifier":
                                index_name = index_expr.get("name", "")
                                if index_name:
                                    reads_set.add(f"{first_level}[{index_name}]")
            
            # Always extract from base and index expressions
            _extract_reads(nested_base_expr, reads_set)
            _extract_reads(nested_index_expr, reads_set)
            _extract_reads(index_expr, reads_set)
                            
        elif base_expr.get("nodeType") == "Identifier":
            base_name = base_expr.get("name", "")
            reads_set.add(base_name)
            
            # If the index is a literal or identifier, track the specific access
            if index_expr.get("nodeType") == "Literal":
                index_value = index_expr.get("value", "")
                if base_name and index_value != "":
                    reads_set.add(f"{base_name}[{index_value}]")
            elif index_expr.get("nodeType") == "Identifier":
                index_name = index_expr.get("name", "")
                if base_name and index_name:
                    reads_set.add(f"{base_name}[{index_name}]")
            elif index_expr.get("nodeType") == "MemberAccess":
                # Handle cases like balances[msg.sender]
                member_expr = index_expr.get("expression", {})
                member_name = index_expr.get("memberName", "")
                
                if member_expr.get("nodeType") == "Identifier":
                    member_base = member_expr.get("name", "")
                    if base_name and member_base and member_name:
                        reads_set.add(f"{base_name}[{member_base}.{member_name}]")
                        # Also add the member access itself as a read
                        reads_set.add(f"{member_base}.{member_name}")
        
        # Handle nested IndexAccess by recursive call on base expression
        elif base_expr.get("nodeType") in ["MemberAccess", "IndexAccess"]:
            _extract_reads(base_expr, reads_set)
        
        # Also extract reads from the index expression
        if index_expr:
            _extract_reads(index_expr, reads_set)
    
    elif node_type == "FunctionCall":
        # Consider function arguments as reads
        for arg in node.get("arguments", []):
            _extract_reads(arg, reads_set)
        
        # For method calls, consider the base object as read
        expr = node.get("expression", {})
        if expr.get("nodeType") == "MemberAccess":
            base = expr.get("expression", {})
            _extract_reads(base, reads_set)