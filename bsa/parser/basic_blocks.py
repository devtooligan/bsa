"""
Basic block functionality for BSA.
"""

def classify_statements(statements):
    """
    Classify raw statements from a function's body into basic types.
    
    Args:
        statements (list): List of raw statement nodes from body_raw
        
    Returns:
        list: List of dictionaries with 'type' and 'node' keys
    """
    typed_statements = []
    
    for node in statements:
        node_type = node.get("nodeType", "Unknown")
        statement_type = "Unknown"
        
        # Classify based on nodeType
        if node_type == "ExpressionStatement":
            # Check if it's an assignment
            expression = node.get("expression", {})
            if expression.get("nodeType") == "Assignment":
                statement_type = "Assignment"
            elif expression.get("nodeType") == "FunctionCall":
                statement_type = "FunctionCall"
            else:
                statement_type = "Expression"
        elif node_type == "EmitStatement":
            # Emit statements are now properly identified
            statement_type = "EmitStatement"
        elif node_type == "IfStatement":
            statement_type = "IfStatement"
        elif node_type == "Return" or node_type == "ReturnStatement":
            statement_type = "Return"
        elif node_type == "VariableDeclarationStatement":
            statement_type = "VariableDeclaration"
        elif node_type == "ForStatement":
            statement_type = "ForLoop"
        elif node_type == "WhileStatement":
            statement_type = "WhileLoop"
        elif node_type == "Block":
            # Recursively classify block statements
            statement_type = "Block"
            # We don't add nested statements as separate entries to avoid duplicates
            # They will be processed during SSA analysis as needed
        
        typed_statements.append({
            "type": statement_type,
            "node": node
        })
        
    return typed_statements
    
def get_statement_type(stmt):
    """
    Helper method to get the type of a statement.
    
    Args:
        stmt (dict): Statement node
        
    Returns:
        str: Statement type
    """
    node_type = stmt.get("nodeType", "Unknown")
    
    if node_type == "ExpressionStatement":
        expression = stmt.get("expression", {})
        if expression.get("nodeType") == "Assignment":
            return "Assignment"
        elif expression.get("nodeType") == "FunctionCall":
            return "FunctionCall"
        else:
            return "Expression"
    elif node_type == "IfStatement":
        return "IfStatement"
    elif node_type == "Return" or node_type == "ReturnStatement":
        return "Return"
    elif node_type == "VariableDeclarationStatement":
        return "VariableDeclaration"
    elif node_type == "ForStatement":
        return "ForLoop"
    elif node_type == "WhileStatement":
        return "WhileLoop"
    elif node_type == "Block":
        return "Block"
    
    return "Unknown"

def split_into_basic_blocks(statements_typed):
    """
    Split typed statements into basic blocks based on control flow, function calls, emit events, and state writes.
    
    Args:
        statements_typed (list): List of typed statement dictionaries
        
    Returns:
        list: List of basic block dictionaries
    """
    # Control flow statement types that terminate a basic block
    block_terminators = ["IfStatement", "ForLoop", "WhileLoop", "Return", "EmitStatement"]
    # Statement types that also terminate a block
    additional_terminators = ["FunctionCall", "Assignment", "VariableDeclaration"]
    
    basic_blocks = []
    current_block = {
        "id": "Block0",
        "statements": [],
        "terminator": None
    }
    
    block_counter = 0
    
    for i, statement in enumerate(statements_typed):
        # Add statement to current block
        current_block["statements"].append(statement)
        
        # Check if this statement is a block terminator
        is_terminator = False
        terminator_type = None
        
        # Traditional control flow terminators
        if statement["type"] in block_terminators:
            is_terminator = True
            terminator_type = statement["type"]
        
        # Additional terminators: function calls and assignments
        elif statement["type"] in additional_terminators:
            # Only terminate if not the last statement (no need to split after the last statement)
            if i < len(statements_typed) - 1:
                is_terminator = True
                terminator_type = statement["type"]
                
                # Special handling for emit events
                if statement["type"] == "EmitStatement":
                    # Mark specifically as an emit terminator for better clarity
                    terminator_type = "EmitStatement"
        
        # If this is a terminator and we need to start a new block
        if is_terminator:
            # Set terminator type for diagnostics
            current_block["terminator"] = terminator_type
            
            # Add current block to blocks list
            basic_blocks.append(current_block)
            
            # Start a new block
            block_counter += 1
            current_block = {
                "id": f"Block{block_counter}",
                "statements": [],
                "terminator": None
            }
    
    # Add the last block if it has statements
    if current_block["statements"]:
        basic_blocks.append(current_block)
    
    return basic_blocks