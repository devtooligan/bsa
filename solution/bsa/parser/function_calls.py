"""
Function call handling for BSA.
"""

def classify_and_add_calls(basic_blocks, function_map):
    """
    Classify function calls in basic blocks and enhance SSA statements.
    
    Args:
        basic_blocks (list): List of basic block dictionaries with SSA statements
        function_map (dict): Mapping of function names to ASTNodes
        
    Returns:
        list: List of basic block dictionaries with enhanced SSA statements
    """
    if not basic_blocks:
        return []
    
    # Tracks the next return value version
    ret_counter = 0
    
    for block in basic_blocks:
        # Find function call statements, revert statements, and external calls
        function_calls = []
        revert_calls = []  # Track revert calls separately
        external_calls = [] # Track external calls separately
        for i, stmt in enumerate(block.get("statements", [])):
            if stmt.get("type") == "FunctionCall":
                function_calls.append(i)
            elif stmt.get("type") == "Revert":
                # Track revert calls so we can format them specially
                revert_calls.append(i)
            elif stmt.get("type") == "ExternalCall":
                # Track external calls so we can format them specially
                external_calls.append(i)
        
        # Skip if there are no function calls, revert calls, or external calls
        if not function_calls and not revert_calls and not external_calls:
            continue
        
        # Get the list of SSA statements to modify
        ssa_statements = block.get("ssa_statements", [])
        if not ssa_statements:
            continue
        
        # Create modified statements list
        modified_statements = list(ssa_statements)
        
        # Map function calls to SSA statements
        call_stmt_indices = []
        for i, stmt in enumerate(ssa_statements):
            if ("call(" in stmt and ("= call(" in stmt or stmt.startswith("call("))):
                call_stmt_indices.append(i)
        
        # Process each function call
        for call_idx in range(min(len(function_calls), len(call_stmt_indices))):
            stmt_idx = call_stmt_indices[call_idx]
            stmt_node_idx = function_calls[call_idx]
            
            # Get the function call node
            call_node = block["statements"][stmt_node_idx]["node"]
            
            # Get the expression containing the function call
            expr = call_node.get("expression", {})
            
            # Handle various node types that represent function calls
            is_external_call = False
            external_call_type = None
            external_call_name = None
            
            # Check for direct member access (like owner.transfer(amount))
            if expr.get("nodeType") == "ExpressionStatement":
                inner_expr = expr.get("expression", {})
                if inner_expr.get("nodeType") == "MemberAccess":
                    member_name = inner_expr.get("memberName", "")
                    if member_name in ["transfer", "send", "call", "delegatecall", "staticcall"]:
                        is_external_call = True
                        external_call_type = "low_level_external"
                        base_expr = inner_expr.get("expression", {})
                        if base_expr.get("nodeType") == "Identifier":
                            base_name = base_expr.get("name", "address")
                            external_call_name = f"{base_name}.{member_name}"
            
            # Continue with the normal flow for FunctionCall
            if expr.get("nodeType") == "FunctionCall":
                func_expr = expr.get("expression", {})
                
                # Determine the type of function call
                call_type = "unknown"
                call_name = "unknown"
                
                # Collect argument values for more informative call statements
                args = []
                for arg in expr.get("arguments", []):
                    if arg.get("nodeType") == "Identifier":
                        args.append(arg.get("name", ""))
                    elif arg.get("nodeType") == "Literal":
                        args.append(str(arg.get("value", "")))
                
                # Function name and target analysis
                if func_expr.get("nodeType") == "Identifier":
                    # Direct function call: foo()
                    call_name = func_expr.get("name", "unknown")
                    
                    # Special handling for revert/require
                    if call_name in ["revert", "require"]:
                        # Process them but mark as "revert" call type, not "external"
                        call_type = "revert"
                        
                    if call_name in function_map:
                        call_type = "internal"
                    else:
                        call_type = "external"
                elif func_expr.get("nodeType") == "MemberAccess":
                    # Member function call: obj.foo()
                    member_name = func_expr.get("memberName", "unknown")
                    call_name = member_name
                    
                    # Check if this is a special call
                    if member_name in ["call", "send", "transfer"]:
                        call_type = "low_level_external"
                    elif member_name == "delegatecall":
                        call_type = "delegatecall"
                    elif member_name == "staticcall":
                        call_type = "staticcall"
                    else:
                        # Check if this is a call on a contract/interface type
                        base_expr = func_expr.get("expression", {})
                        # For calls like IA(a).hello()
                        if base_expr.get("nodeType") == "FunctionCall":
                            # This is a cast to contract type, definitely external
                            call_type = "external"
                        elif base_expr.get("nodeType") == "Identifier":
                            # For contract instance variables
                            base_name = base_expr.get("name", "")
                            # Check type information if available
                            type_descriptions = base_expr.get("typeDescriptions", {})
                            type_string = type_descriptions.get("typeString", "")
                            
                            # If type string indicates contract or interface, it's external
                            if "contract" in type_string.lower() or "interface" in type_string.lower():
                                call_type = "external"
                            elif base_name in function_map:
                                call_type = "internal"
                            else:
                                # Default to external if not recognized as internal
                                call_type = "external"
                
                # Update the SSA statement with the call classification
                call_stmt = ssa_statements[stmt_idx]
                
                # Check if this is a function call statement
                if "call(" in call_stmt:
                    # Create enhanced call statement based on type and name
                    enhanced_stmt = ""
                    
                    # Handle both formats: "ret_1 = call(...)" and "call(...)"
                    if "= call(" in call_stmt:
                        ret_part = call_stmt.split(" = ")[0]
                        enhanced_stmt = f"{ret_part} = call[{call_type}]({call_name}"
                    else:
                        enhanced_stmt = f"call[{call_type}]({call_name}"
                    
                    # Extract arguments
                    args_part = ""
                    if "(" in call_stmt:
                        args_part = call_stmt.split("(", 1)[1].strip(")")
                    
                    # Add arguments to the enhanced statement
                    if args_part.strip():
                        enhanced_stmt += f", {args_part}"
                    elif args:
                        # If no args in the statement but AST has args
                        enhanced_stmt += ", " + ", ".join(args)
                    
                    enhanced_stmt += ")"
                    
                    # Use the properly formatted call statement with no special cases
                    # The enhanced_stmt already has the correct format based on the call type and arguments
                    
                    # Replace the statement
                    modified_statements[stmt_idx] = enhanced_stmt
        
        # Update the block with modified statements if we processed function calls
        if function_calls:
            block["ssa_statements"] = modified_statements
        
        # Process external calls if any
        if external_calls:
            # Find existing call statements in SSA
            external_call_indices = []
            for i, stmt in enumerate(block["ssa_statements"]):
                if "call(" in stmt or "= " in stmt:
                    external_call_indices.append(i)
            
            # Process each external call
            for ext_idx in range(min(len(external_calls), len(external_call_indices))):
                stmt_idx = external_call_indices[ext_idx]
                node_idx = external_calls[ext_idx]
                
                # Get the external call node
                ext_node = block["statements"][node_idx]["node"]
                
                # Get the expression containing the function call
                expr = ext_node.get("expression", {})
                
                # Handle both FunctionCall and direct MemberAccess
                if expr.get("nodeType") == "FunctionCall":
                    func_expr = expr.get("expression", {})
                    if func_expr.get("nodeType") == "MemberAccess":
                        member_name = func_expr.get("memberName", "")
                        base_expr = func_expr.get("expression", {})
                        base_name = "address"
                        if base_expr.get("nodeType") == "Identifier":
                            base_name = base_expr.get("name", "address")
                        
                        # Format the external call statement
                        ssa_stmt = block["ssa_statements"][stmt_idx]
                        
                        # Create enhanced external call statement
                        if "= " in ssa_stmt:
                            ret_part = ssa_stmt.split(" = ")[0]
                            ext_stmt = f"{ret_part} = call[low_level_external]({base_name}.{member_name})"
                        else:
                            ext_stmt = f"call[low_level_external]({base_name}.{member_name})"
                        
                        # Update the statement
                        block["ssa_statements"][stmt_idx] = ext_stmt
                        
                elif expr.get("nodeType") == "MemberAccess":
                    member_name = expr.get("memberName", "")
                    base_expr = expr.get("expression", {})
                    base_name = "address"
                    if base_expr.get("nodeType") == "Identifier":
                        base_name = base_expr.get("name", "address")
                    
                    # Format the external call statement
                    ssa_stmt = block["ssa_statements"][stmt_idx]
                    
                    # Create enhanced external call statement
                    if "= " in ssa_stmt:
                        ret_part = ssa_stmt.split(" = ")[0]
                        ext_stmt = f"{ret_part} = call[low_level_external]({base_name}.{member_name})"
                    else:
                        ext_stmt = f"call[low_level_external]({base_name}.{member_name})"
                    
                    # Update the statement
                    block["ssa_statements"][stmt_idx] = ext_stmt
        
        # Process revert statements if any
        if revert_calls:
            # Find existing call statements in SSA that might be reverts
            revert_ssa_indices = []
            for i, stmt in enumerate(block["ssa_statements"]):
                if "call(" in stmt or "= revert" in stmt or "= require" in stmt or "= assert" in stmt:
                    revert_ssa_indices.append(i)
            
            # Process each revert call
            for rev_idx in range(min(len(revert_calls), len(revert_ssa_indices))):
                stmt_idx = revert_ssa_indices[rev_idx]
                node_idx = revert_calls[rev_idx]
                
                # Get the revert node
                revert_node = block["statements"][node_idx]["node"]
                
                # Get the expression containing the function call
                expr = revert_node.get("expression", {})
                if expr.get("nodeType") == "FunctionCall":
                    func_expr = expr.get("expression", {})
                    
                    # Get the function name (revert or require)
                    func_name = "revert"  # Default
                    if func_expr.get("nodeType") == "Identifier":
                        func_name = func_expr.get("name", "revert")
                    
                    # Collect arguments for the revert call
                    args = []
                    for arg in expr.get("arguments", []):
                        if arg.get("nodeType") == "Identifier":
                            args.append(arg.get("name", ""))
                        elif arg.get("nodeType") == "Literal":
                            if isinstance(arg.get("value"), str):
                                args.append(f'"{arg.get("value", "")}"')
                            else:
                                args.append(str(arg.get("value", "")))
                    
                    # Format the revert statement
                    ssa_stmt = block["ssa_statements"][stmt_idx]
                    
                    # Create enhanced revert statement
                    if "= call(" in ssa_stmt:
                        ret_part = ssa_stmt.split(" = ")[0]
                        revert_stmt = f"{ret_part} = {func_name}"
                    else:
                        revert_stmt = func_name
                    
                    # Add arguments if any
                    if args:
                        revert_stmt += " " + ", ".join(args)
                    
                    # Update the statement
                    block["ssa_statements"][stmt_idx] = revert_stmt
    
    return basic_blocks

def inline_internal_calls(basic_blocks, function_map, entrypoints_data=None):
    """
    Inlines the effects of internal function calls into the caller's SSA.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        function_map (dict): Mapping of function names to their ASTNodes
        entrypoints_data (dict, optional): Mapping of function names to their SSA data
        
    Returns:
        list: List of basic block dictionaries with inlined internal calls
    """
    if not basic_blocks or not function_map:
        return basic_blocks
        
    # If entrypoints_data is not provided, we can't inline anything
    if entrypoints_data is None:
        return basic_blocks
        
    # Create a mapping from function name to its SSA data for quick lookup
    function_ssa = {}
    for entry in entrypoints_data:
        entry_name = entry.get("name", "")
        if entry_name and "ssa" in entry:
            function_ssa[entry_name] = entry["ssa"]
        
    # Initialize a counter for generating unique variable versions
    version_counter = {}
    
    # Initialize tracking dictionary to deduplicate arguments in compound operations
    seen_args_by_call = {}
    
    # Process each block for function calls
    for block in basic_blocks:
        # Skip blocks with no SSA statements
        if "ssa_statements" not in block:
            continue
            
        # Get current variable versions from this block
        # Track the highest version of each variable seen in the caller
        for var, version in block.get("ssa_versions", {}).get("writes", {}).items():
            if var not in version_counter:
                version_counter[var] = 0
            version_counter[var] = max(version_counter[var], version)
        
        # Find internal calls in the block
        modified_statements = []
        added_reads = set()
        added_writes = set()
        
        for stmt_idx, stmt in enumerate(block["ssa_statements"]):
            # Check if this is an internal function call
            if "call[internal]" in stmt:
                # Extract function name and arguments
                call_parts = stmt.split("call[internal](")[1].strip(")")
                if "," in call_parts:
                    func_name = call_parts.split(",")[0].strip()
                    args_part = call_parts[len(func_name)+1:].strip()
                    # Ensure proper comma separation between arguments
                    arg_list = [arg.strip() for arg in args_part.split(",") if arg.strip()]
                else:
                    # No comma means it's just a function name with no args, or args without comma
                    parts = call_parts.strip().split()
                    if len(parts) > 1:
                        # Handle case where commas are missing between arguments
                        func_name = parts[0]
                        # Convert space-separated args to a proper list
                        arg_list = parts[1:]
                    else:
                        func_name = call_parts.strip()
                        arg_list = []
                
                # Get the return variable name and version
                ret_var = stmt.split(" = ")[0] if " = " in stmt else "ret_1"
                
                # Look up the function's SSA data
                if func_name in function_ssa:
                    target_ssa = function_ssa[func_name]
                    
                    # Add the original call for reference, but with proper formatting
                    if len(arg_list) > 1:
                        # Format with proper commas
                        func_part = stmt.split("call[internal](")[0] + "call[internal]("
                        args_formatted = func_name + ", " + ", ".join(arg_list)
                        formatted_stmt = func_part + args_formatted + ")"
                        modified_statements.append(formatted_stmt)
                    else:
                        # Keep the original statement
                        modified_statements.append(stmt)
                    
                    # Initialize a map to keep track of state variable versions
                    var_version_map = {}
                    
                    # Process argument versions - track incoming arguments for parameter binding
                    arg_version_map = {}
                    param_to_arg_map = {}  # Maps parameter names to their actual argument names
                    if arg_list:
                        # Map arguments to their respective variables in the callee
                        # Find the function definition to get parameter names
                        func_node = function_map.get(func_name)
                        if func_node:
                            parameters = func_node.get("parameters", {}).get("parameters", [])
                            for i, param in enumerate(parameters):
                                if i < len(arg_list):
                                    param_name = param.get("name", "")
                                    if param_name:
                                        # Extract the base name and version from the argument
                                        arg = arg_list[i]
                                        if "_" in arg:  # Has version number
                                            arg_base, arg_version = arg.rsplit("_", 1)
                                            try:
                                                arg_version = int(arg_version)
                                                # Map parameter to this argument's version
                                                arg_version_map[param_name] = (arg_base, arg_version)
                                                # Also track which parameter maps to which argument name
                                                param_to_arg_map[param_name] = arg_base
                                            except ValueError:
                                                # Not a valid version number
                                                pass
                    
                    # Create a unique key for this function call and statement to track argument usage
                    call_key = f"{func_name}_{stmt_idx}"
                    
                    # Initialize tracking set for this call if it doesn't exist
                    if call_key not in seen_args_by_call:
                        seen_args_by_call[call_key] = set()

                    # Collect all inlined statements from all target blocks
                    all_inlined_statements = []
                    
                    # Track the highest version used for each variable during inlining
                    var_max_version = {var: ver for var, ver in version_counter.items()}
                    
                    # Inline each block from the target function
                    for target_block in target_ssa:
                        target_statements = target_block.get("ssa_statements", [])
                        
                        # Process each statement in the target function
                        for target_stmt in target_statements:
                            # Skip phi functions (they don't transfer well across function boundaries)
                            if "= phi(" in target_stmt:
                                continue
                                
                            # Initialize inlined statement with the original
                            inlined_stmt = target_stmt
                            
                            # Check if this is a compound operation (+=, -=, etc.)
                            is_compound_op = False
                            right_side_vars = []
                            if " = " in inlined_stmt:
                                lhs, rhs = inlined_stmt.split(" = ", 1)
                                # For balanceOf[to] = balanceOf[to] + amount patterns
                                if " + " in rhs:
                                    is_compound_op = True
                                    op_parts = rhs.split(" + ")
                                    # Extract variable names without version numbers
                                    right_side_vars = [part.split("_")[0] for part in op_parts if "_" in part]
                                # For balanceOf[from] = balanceOf[from] - amount patterns
                                elif " - " in rhs:
                                    is_compound_op = True
                                    op_parts = rhs.split(" - ")
                                    # Extract variable names without version numbers
                                    right_side_vars = [part.split("_")[0] for part in op_parts if "_" in part]
                            
                            # We're already using the call_key from the outer scope for this function call
                            
                            # Bind arguments to parameters based on the mapping we created
                            for param_name, (arg_base, arg_version) in arg_version_map.items():
                                # Replace parameter references with argument references
                                param_pattern = f"{param_name}_"
                                
                                # Only replace whole variables with version numbers
                                # This avoids issues with partial name matches
                                for i in range(10):  # Assuming versions 0-9 for simplicity
                                    param_ref = f"{param_name}_{i}"
                                    if param_ref in inlined_stmt:
                                        # For compound operations, ensure we use the correct variable name
                                        # and eliminate duplication of variables in the output
                                        if is_compound_op:
                                            # If this variable is already seen in this call or is on right side vars,
                                            # don't add duplicates in compound operations
                                            if arg_base in seen_args_by_call[call_key]:
                                                # Skip this replacement entirely to avoid duplication
                                                continue
                                            else:
                                                # First occurrence - use actual arg_base
                                                replacement = f"{arg_base}_{arg_version}"
                                                # Mark as seen to avoid duplicates
                                                seen_args_by_call[call_key].add(arg_base)
                                        else:
                                            # Standard replacement with argument
                                            replacement = f"{arg_base}_{arg_version}"
                                        
                                        inlined_stmt = inlined_stmt.replace(param_ref, replacement)
                            
                            # Process variables in the function body (not parameters)
                            # Extract the variable being written to (if any)
                            written_var = None
                            if " = " in inlined_stmt:
                                written_part = inlined_stmt.split(" = ")[0]
                                if "_" in written_part:
                                    written_var, written_ver_str = written_part.rsplit("_", 1)
                                    try:
                                        written_ver = int(written_ver_str)
                                    except ValueError:
                                        written_var = None
                            
                            # Handle state variables that need version updates
                            var_versions_to_update = {}
                            
                            # First collect all variables that need updating in this statement
                            for var in version_counter:
                                var_pattern = f"{var}_"
                                if var_pattern in inlined_stmt:
                                    # Find all occurrences of this variable with its version
                                    for i in range(10):  # Assuming versions 0-9 for simplicity
                                        old_var = f"{var}_{i}"
                                        if old_var in inlined_stmt:
                                            if var == written_var:
                                                # This is a write, increment the version counter
                                                version_counter[var] += 1
                                                var_max_version[var] = version_counter[var]
                                                var_versions_to_update[old_var] = f"{var}_{var_max_version[var]}"
                                                # Track this as a write
                                                added_writes.add(var)
                                            else:
                                                # This is a read, use either the latest caller version or a new incremented version
                                                current_ver = var_max_version.get(var, 0)
                                                var_versions_to_update[old_var] = f"{var}_{current_ver}"
                                                # Track this as a read
                                                added_reads.add(var)
                            
                            # Now apply all updates at once to avoid partial replacements
                            for old_var, new_var in var_versions_to_update.items():
                                # We need to ensure we replace only whole variable references
                                # This is a simplified approach, a more robust solution would use regex
                                inlined_stmt = inlined_stmt.replace(old_var, new_var)
                            
                            # Add the inlined statement to our collected inlined statements
                            all_inlined_statements.append(inlined_stmt)
                            
                            # Directly update accesses based on this statement
                            # Extract variable from the statement for writes
                            if " = " in inlined_stmt:
                                var_name = None
                                if "_" in inlined_stmt.split(" = ")[0]:
                                    var_name = inlined_stmt.split(" = ")[0].split("_")[0]
                                if var_name and "accesses" in block and "writes" in block["accesses"]:
                                    if var_name not in block["accesses"]["writes"]:
                                        block["accesses"]["writes"].append(var_name)
                            
                            # Extract reads from right-hand side and add to accesses
                            if " = " in inlined_stmt:
                                rhs = inlined_stmt.split(" = ")[1]
                                for part in rhs.split():
                                    if "_" in part:
                                        var_name = part.split("_")[0]
                                        added_reads.add(var_name)
                    
                    # Add all the inlined statements after the original call
                    modified_statements.extend(all_inlined_statements)
                else:
                    # Keep the original call if we can't inline it
                    modified_statements.append(stmt)
            else:
                # Keep non-call statements
                modified_statements.append(stmt)
        
        # Update the block with inlined statements
        if modified_statements:
            block["ssa_statements"] = modified_statements
            
            # Update block accesses with inlined variables
            if "accesses" not in block:
                block["accesses"] = {"reads": [], "writes": []}
            
            # Ensure reads and writes lists exist
            if "reads" not in block["accesses"]:
                block["accesses"]["reads"] = []
            if "writes" not in block["accesses"]:
                block["accesses"]["writes"] = []
            
            # Update with added reads and writes, ensuring clean access tracking
            reads = set(block["accesses"]["reads"])
            writes = set(block["accesses"]["writes"])
            
            # Filter out call markers and function call syntax from added_reads
            filtered_added_reads = set()
            for read in added_reads:
                if "call[" in read or "call(" in read or ")" in read:
                    continue
                filtered_added_reads.add(read)
            
            # Update with filtered reads
            reads.update(filtered_added_reads)
            writes.update(added_writes)
            
            # Final filtering to ensure clean output
            reads_filtered = set(read for read in reads if not (
                "call[" in read or "call(" in read or ")" in read
            ))
            
            # Apply the filtered sets
            block["accesses"]["reads"] = list(reads_filtered)
            block["accesses"]["writes"] = list(writes)
    
    return basic_blocks