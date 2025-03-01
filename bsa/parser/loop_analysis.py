"""
Loop analysis functionality for BSA.
"""

def analyze_loop_calls(basic_blocks):
    """
    Enhance loop handling to track nested function call effects across iterations.
    
    Args:
        basic_blocks (list): List of basic block dictionaries with control flow
        
    Returns:
        list: List of basic block dictionaries with enhanced loop handling for calls
    """
    if not basic_blocks:
        return []
    
    # Build a dictionary to map block IDs to blocks
    block_map = {block["id"]: block for block in basic_blocks}
    
    # Identify loop header blocks and their bodies
    loop_headers = []
    loop_bodies = []
    for block in basic_blocks:
        if block.get("is_loop_header", False):
            loop_headers.append(block)
            
            # Find the body blocks for this header by analyzing terminators
            body_blocks = []
            if block.get("terminator", ""):
                terminator = block["terminator"]
                if "then goto " in terminator and " else goto " in terminator:
                    # Extract the body block ID
                    body_id = terminator.split("then goto ")[1].split(" else goto ")[0]
                    if body_id in block_map:
                        body_blocks.append(block_map[body_id])
                        
                        # Add any blocks that are part of the body by following terminators
                        current = block_map[body_id]
                        while current.get("terminator", "").startswith("goto ") and not current.get("is_loop_exit", False):
                            next_id = current["terminator"].split("goto ")[1]
                            if next_id in block_map and not block_map[next_id].get("is_loop_header", False):
                                current = block_map[next_id]
                                body_blocks.append(current)
                            else:
                                break
            
            loop_bodies.append(body_blocks)
    
    # Process each loop header and its body blocks
    for i, header in enumerate(loop_headers):
        if i >= len(loop_bodies):
            continue
            
        body_blocks = loop_bodies[i]
        
        # Check for function calls in loop body blocks
        has_external_calls = False
        external_call_types = []
        modified_state_vars = set()
        
        for body_block in body_blocks:
            # Check statements for external calls
            for stmt in body_block.get("ssa_statements", []):
                # Detect call types
                if "call[external]" in stmt or "call[low_level_external]" in stmt or "call[delegatecall]" in stmt or "call[staticcall]" in stmt:
                    has_external_calls = True
                    if "call[external]" in stmt:
                        external_call_types.append("external")
                    elif "call[low_level_external]" in stmt:
                        external_call_types.append("low_level_external")
                    elif "call[delegatecall]" in stmt:
                        external_call_types.append("delegatecall")
                    elif "call[staticcall]" in stmt:
                        external_call_types.append("staticcall")
        
        # If there are external calls in the loop body, we need to add phi functions
        # for all state variables to the loop header, since external calls may modify any state
        if has_external_calls:
            # Find all state variables that could be affected
            for block in basic_blocks:
                for stmt in block.get("ssa_statements", []):
                    for var in block.get("accesses", {}).get("writes", []):
                        if f"{var}_" in stmt and " = " in stmt:
                            modified_state_vars.add(var)
            
            # Add these variables to the loop header's access list to ensure phi functions
            # will be created for them during phi insertion
            reads = header.get("accesses", {}).get("reads", [])
            writes = header.get("accesses", {}).get("writes", [])
            
            header_accesses = {"reads": list(set(reads)), "writes": list(set(writes + list(modified_state_vars)))}
            header["accesses"] = header_accesses
            
            # Mark the header to indicate it has potential external call effects
            header["has_external_call_effects"] = True
            header["external_call_types"] = external_call_types
            
    return basic_blocks