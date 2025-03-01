"""
Control flow functionality for BSA.
"""

from bsa.parser.basic_blocks import get_statement_type

def finalize_terminators(basic_blocks):
    """
    Ensure all blocks have correct terminators for complete control flow.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of basic block dictionaries with updated terminators
    """
    if not basic_blocks:
        return []
    
    # Map blocks by ID for easier lookup
    block_ids = {block["id"]: idx for idx, block in enumerate(basic_blocks)}
    
    # Process each block to ensure it has a proper terminator
    for idx, block in enumerate(basic_blocks):
        # Skip if block already has a complete terminator (not just a type)
        if isinstance(block.get("terminator"), str) and ("goto" in block["terminator"] or block["terminator"] == "return"):
            continue
            
        # Special handling for if statements and loops - they already have terminators set
        if block.get("terminator") in ["IfStatement", "ForLoop", "WhileLoop"]:
            # These should have been processed by refine_blocks_with_control_flow
            continue
            
        # Handle return statements
        if block.get("terminator") == "Return":
            # Update the terminator to the explicit "return" value
            block["terminator"] = "return"
            continue
        
        # Special handling for emit statements
        if block.get("terminator") == "EmitStatement":
            # Convert EmitStatement to a goto to the next block
            if idx < len(basic_blocks) - 1:
                # Not the last block, so add goto next block
                next_block = basic_blocks[idx + 1]
                block["terminator"] = f"goto {next_block['id']}"
            else:
                # Last block in function, should return
                block["terminator"] = "return"
            
        # For all other blocks, determine if they should goto next block or return
        if idx < len(basic_blocks) - 1:
            # Not the last block, so add goto next block
            next_block = basic_blocks[idx + 1]
            block["terminator"] = f"goto {next_block['id']}"
        else:
            # Last block in function, should return
            block["terminator"] = "return"
    
    return basic_blocks

def refine_blocks_with_control_flow(basic_blocks):
    """
    Refine basic blocks to handle control flow splits from IfStatements and Loops.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of refined basic block dictionaries with control flow
    """
    if not basic_blocks:
        return []
        
    refined_blocks = []
    block_counter = len(basic_blocks)
    
    for block_idx, block in enumerate(basic_blocks):
        # Check for various control flow statements in this block
        has_if = "IfStatement" in [s["type"] for s in block["statements"]]
        has_for_loop = "ForLoop" in [s["type"] for s in block["statements"]]
        has_while_loop = "WhileLoop" in [s["type"] for s in block["statements"]]
        
        # If this block has no control flow statements, add it directly
        if not (has_if or has_for_loop or has_while_loop):
            refined_blocks.append(block)
            continue
            
        # Handle if statement blocks
        if has_if:
            # Find the index of the IfStatement
            if_idx = None
            for idx, statement in enumerate(block["statements"]):
                if statement["type"] == "IfStatement":
                    if_idx = idx
                    break
            
            # Extract the if statement and its condition
            if_statement = block["statements"][if_idx]
            condition = if_statement["node"].get("condition", {})
            
            # Extract statements before the if
            pre_if_statements = block["statements"][:if_idx]
            
            # Create a conditional block with the if statement
            conditional_block = {
                "id": block["id"],
                "statements": pre_if_statements + [if_statement],
                "terminator": "conditional"
            }
            
            # Create true branch block
            true_block_id = f"Block{block_counter}"
            block_counter += 1
            
            true_body = if_statement["node"].get("trueBody", {})
            true_statements = true_body.get("statements", [])
            true_typed_statements = [{"type": get_statement_type(stmt), "node": stmt} for stmt in true_statements]
            
            true_block = {
                "id": true_block_id,
                "statements": true_typed_statements,
                "terminator": None,
                "branch_type": "true"
            }
            
            # Create false branch block
            false_block_id = f"Block{block_counter}"
            block_counter += 1
            
            false_body = if_statement["node"].get("falseBody", {})
            false_statements = false_body.get("statements", []) if false_body else []
            false_typed_statements = [{"type": get_statement_type(stmt), "node": stmt} for stmt in false_statements]
            
            false_block = {
                "id": false_block_id,
                "statements": false_typed_statements,
                "terminator": None,
                "branch_type": "false"
            }
            
            # Update the conditional block's terminator with goto information
            conditional_block["terminator"] = f"if {condition} then goto {true_block_id} else goto {false_block_id}"
            
            # Check if there are statements after the if in the original block
            next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
            
            # Add blocks to refined list
            refined_blocks.append(conditional_block)
            refined_blocks.append(true_block)
            refined_blocks.append(false_block)
            
            # Set up jumps to the next block if it exists
            if next_block_id:
                if not true_block["terminator"]:
                    true_block["terminator"] = f"goto {next_block_id}"
                if not false_block["terminator"]:
                    false_block["terminator"] = f"goto {next_block_id}"
        
        # Handle for loop blocks
        elif has_for_loop:
            # Find the index of the ForLoop
            loop_idx = None
            for idx, statement in enumerate(block["statements"]):
                if statement["type"] == "ForLoop":
                    loop_idx = idx
                    break
            
            # Extract the for loop statement and its components
            loop_statement = block["statements"][loop_idx]
            loop_node = loop_statement["node"]
            
            # Get loop components: initialization, condition, increment
            initialization = loop_node.get("initializationExpression", {})
            condition = loop_node.get("condition", {})
            increment = loop_node.get("loopExpression", {})
            
            # Extract statements before the loop
            pre_loop_statements = block["statements"][:loop_idx]
            
            # Create block for initialization
            init_block = {
                "id": block["id"],
                "statements": pre_loop_statements + [{
                    "type": get_statement_type(initialization), 
                    "node": initialization
                }] if initialization else pre_loop_statements,
                "terminator": None,
                "is_loop_init": True
            }
            
            # Create loop header block with condition check
            header_block_id = f"Block{block_counter}"
            block_counter += 1
            
            header_block = {
                "id": header_block_id,
                "statements": [{
                    "type": "Expression", 
                    "node": {"nodeType": "Expression", "expression": condition}
                }] if condition else [],
                "terminator": None,
                "is_loop_header": True
            }
            
            # Create loop body block
            body_block_id = f"Block{block_counter}"
            block_counter += 1
            
            body = loop_node.get("body", {})
            body_statements = body.get("statements", []) if body else []
            body_typed_statements = [{"type": get_statement_type(stmt), "node": stmt} for stmt in body_statements]
            
            # Ensure proper accesses for loop body statements (especially number++)
            body_reads = set()
            body_writes = set()
            
            # Check for unary operations like number++ in loop body
            for stmt in body_statements:
                if stmt.get("nodeType") == "ExpressionStatement":
                    expr = stmt.get("expression", {})
                    if expr.get("nodeType") == "UnaryOperation" and expr.get("operator") in ["++", "--"]:
                        sub_expr = expr.get("subExpression", {})
                        if sub_expr.get("nodeType") == "Identifier":
                            var_name = sub_expr.get("name", "")
                            body_reads.add(var_name)
                            body_writes.add(var_name)
            
            body_block = {
                "id": body_block_id,
                "statements": body_typed_statements,
                "terminator": None,
                "is_loop_body": True,
                "accesses": {
                    "reads": list(body_reads),
                    "writes": list(body_writes)
                }
            }
            
            # Create loop increment block
            increment_block_id = f"Block{block_counter}"
            block_counter += 1
            
            increment_block = {
                "id": increment_block_id,
                "statements": [{
                    "type": get_statement_type(increment), 
                    "node": increment
                }] if increment else [],
                "terminator": None,
                "is_loop_increment": True
            }
            
            # Create exit block for code after the loop
            exit_block_id = f"Block{block_counter}"
            block_counter += 1
            
            exit_block = {
                "id": exit_block_id,
                "statements": [],  # No statements yet, will be connected to next block
                "terminator": None,
                "is_loop_exit": True
            }
            
            # Set up the loop control flow connections
            init_block["terminator"] = f"goto {header_block_id}"
            header_block["terminator"] = f"if {condition} then goto {body_block_id} else goto {exit_block_id}"
            body_block["terminator"] = f"goto {increment_block_id}"
            increment_block["terminator"] = f"goto {header_block_id}"  # Loop back edge
            
            # Check if there are statements after the loop in the original block
            next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
            
            # Connect the exit block to the next block if it exists
            if next_block_id:
                exit_block["terminator"] = f"goto {next_block_id}"
            
            # Add all loop blocks to refined list
            refined_blocks.append(init_block)
            refined_blocks.append(header_block)
            refined_blocks.append(body_block)
            refined_blocks.append(increment_block)
            refined_blocks.append(exit_block)
        
        # Handle while loop blocks
        elif has_while_loop:
            # Find the index of the WhileLoop
            loop_idx = None
            for idx, statement in enumerate(block["statements"]):
                if statement["type"] == "WhileLoop":
                    loop_idx = idx
                    break
            
            # Extract the while loop statement and its components
            loop_statement = block["statements"][loop_idx]
            loop_node = loop_statement["node"]
            
            # Get loop condition
            condition = loop_node.get("condition", {})
            
            # Extract statements before the loop
            pre_loop_statements = block["statements"][:loop_idx]
            
            # Create block for pre-loop code
            pre_block = {
                "id": block["id"],
                "statements": pre_loop_statements,
                "terminator": None
            }
            
            # Create loop header block with condition check
            header_block_id = f"Block{block_counter}"
            block_counter += 1
            
            header_block = {
                "id": header_block_id,
                "statements": [{
                    "type": "Expression", 
                    "node": {"nodeType": "Expression", "expression": condition}
                }] if condition else [],
                "terminator": None,
                "is_loop_header": True
            }
            
            # Create loop body block
            body_block_id = f"Block{block_counter}"
            block_counter += 1
            
            body = loop_node.get("body", {})
            body_statements = body.get("statements", []) if body else []
            body_typed_statements = [{"type": get_statement_type(stmt), "node": stmt} for stmt in body_statements]
            
            body_block = {
                "id": body_block_id,
                "statements": body_typed_statements,
                "terminator": None,
                "is_loop_body": True
            }
            
            # Create exit block for code after the loop
            exit_block_id = f"Block{block_counter}"
            block_counter += 1
            
            exit_block = {
                "id": exit_block_id,
                "statements": [],  # No statements yet, will be connected to next block
                "terminator": None,
                "is_loop_exit": True
            }
            
            # Set up the loop control flow connections
            pre_block["terminator"] = f"goto {header_block_id}"
            header_block["terminator"] = f"if {condition} then goto {body_block_id} else goto {exit_block_id}"
            body_block["terminator"] = f"goto {header_block_id}"  # Loop back edge
            
            # Check if there are statements after the loop in the original block
            next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
            
            # Connect the exit block to the next block if it exists
            if next_block_id:
                exit_block["terminator"] = f"goto {next_block_id}"
            
            # Add all loop blocks to refined list
            refined_blocks.append(pre_block)
            refined_blocks.append(header_block)
            refined_blocks.append(body_block)
            refined_blocks.append(exit_block)
    
    return refined_blocks