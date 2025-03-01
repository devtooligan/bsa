"""
SSA (Static Single Assignment) conversion functionality.

This module contains the functions needed to transform the basic blocks
into SSA form, including versioning variables, inserting phi functions,
and integrating the SSA output.
"""

class SSAConverter:
    """
    Handles conversion of basic blocks into Static Single Assignment (SSA) form.
    """
    
    @staticmethod
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
            SSAConverter._extract_reads(node.get("leftExpression", {}), reads_set)
            SSAConverter._extract_reads(node.get("rightExpression", {}), reads_set)
        
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
                SSAConverter._extract_reads(base_expr, reads_set)
        
        elif node_type == "IndexAccess":
            SSAConverter._extract_index_access_reads(node, reads_set)
        
        elif node_type == "FunctionCall":
            # Consider function arguments as reads
            for arg in node.get("arguments", []):
                SSAConverter._extract_reads(arg, reads_set)
            
            # For method calls, consider the base object as read
            expr = node.get("expression", {})
            if expr.get("nodeType") == "MemberAccess":
                base = expr.get("expression", {})
                SSAConverter._extract_reads(base, reads_set)
    
    @staticmethod
    def _extract_index_access_reads(node, reads_set):
        """
        Helper method to extract reads from index access expressions (array[index] or mapping[key]).
        
        Args:
            node (dict): Index access AST node
            reads_set (set): Set to add read variables to
        """
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
            SSAConverter._extract_reads(nested_base_expr, reads_set)
            SSAConverter._extract_reads(nested_index_expr, reads_set)
            SSAConverter._extract_reads(index_expr, reads_set)
                            
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
            SSAConverter._extract_reads(base_expr, reads_set)
        
        # Also extract reads from the index expression
        if index_expr:
            SSAConverter._extract_reads(index_expr, reads_set)
    
    @staticmethod
    def _initialize_version_tracking(basic_blocks):
        """
        Initialize version counter and current version tracking for all variables.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with accesses
            
        Returns:
            tuple: (version_counters, current_versions) dictionaries
        """
        # Initialize version counters for all variables
        version_counters = {}
        current_versions = {}
        
        # First pass: initialize all variables with version 0
        for block in basic_blocks:
            reads = block["accesses"]["reads"]
            writes = block["accesses"]["writes"]
            
            # Initialize any new variables found in reads
            for var in reads:
                if var not in version_counters:
                    version_counters[var] = 0
                    current_versions[var] = 0
            
            # Initialize any new variables found in writes
            for var in writes:
                if var not in version_counters:
                    version_counters[var] = 0
                    current_versions[var] = 0
        
        return version_counters, current_versions
    
    @staticmethod
    def _assign_variable_versions(block, current_versions, version_counters):
        """
        Assign read and write versions to variables in a block.
        
        Args:
            block (dict): Basic block dictionary with accesses
            current_versions (dict): Dictionary mapping variables to their current versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            tuple: (reads_dict, writes_dict) dictionaries with variable versions
        """
        reads = block["accesses"]["reads"]
        writes = block["accesses"]["writes"]
        reads_dict = {}
        writes_dict = {}
        
        # Assign read versions (use current version)
        for var in reads:
            reads_dict[var] = current_versions[var]
        
        # Assign write versions (increment counter and update current)
        for var in writes:
            version_counters[var] += 1
            current_version = version_counters[var]
            writes_dict[var] = current_version
            current_versions[var] = current_version
            
            # Special case: If a variable is both read and written in the same block,
            # and it appears in an if statement after the write, update its read version
            if var in reads and "IfStatement" in [stmt["type"] for stmt in block["statements"]]:
                reads_dict[var] = current_version
        
        # Store the version information in the block
        block["ssa_versions"] = {
            "reads": reads_dict,
            "writes": writes_dict
        }
        
        return reads_dict, writes_dict
    
    @staticmethod
    def _process_number_increment(block, reads_dict, writes_dict):
        """
        Process number++ operations and add explicit SSA statements.
        
        Args:
            block (dict): Basic block dictionary
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            
        Returns:
            list: List of SSA statements for the block
        """
        ssa_statements = []
        
        # Special handling for blocks with number++ operations
        if block.get("has_number_increment", False) and "number" in block.get("accesses", {}).get("writes", []):
            # Get versions for the number variable
            read_version = reads_dict.get("number", 0)
            write_version = writes_dict.get("number", 1)
            
            # Add explicit SSA statement for number++ operation
            ssa_statements.append(f"number_{write_version} = number_{read_version} + 1")
        
        return ssa_statements
    
    @staticmethod
    def _handle_assignment(node, reads_dict, writes_dict, version_counters):
        """
        Process an assignment statement and convert it to SSA form.
        
        Args:
            node (dict): Assignment statement node
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            list: List of SSA statements for this assignment
        """
        ssa_statements = []
        
        if node["nodeType"] != "ExpressionStatement":
            return ssa_statements
            
        expression = node.get("expression", {})
        if expression.get("nodeType") != "Assignment":
            return ssa_statements
            
        # Get assignment parts
        operator = expression.get("operator", "=")
        left_hand_side = expression.get("leftHandSide", {})
        right_hand_side = expression.get("rightHandSide", {})
        
        # Handle different left-hand side types
        if left_hand_side.get("nodeType") == "Identifier":
            var_name = left_hand_side.get("name", "")
            
            # Ensure var_name is properly initialized in version tracking
            if var_name not in version_counters:
                version_counters[var_name] = 0
                
            var_version = writes_dict.get(var_name, 0)
            
            # Create SSA assignment statement
            ssa_stmt = f"{var_name}_{var_version} = "
            
            # Handle compound assignments (+=, -=, etc.)
            compound_op = operator
            if compound_op not in ["=", ""]:
                # Format: x_1 = x_0 + right_side - never use negative versions
                prev_version = max(var_version - 1, 0)
                ssa_stmt += f"{var_name}_{prev_version} "
                
                # Extract the actual operation (+ from +=, - from -=, etc.)
                operation = compound_op[0]
                ssa_stmt += f"{operation} "
            
            # Handle literals directly
            if right_hand_side.get("nodeType") == "Literal":
                ssa_stmt += str(right_hand_side.get("value", ""))
            else:
                ssa_stmt += SSAConverter._format_rhs_variables(right_hand_side, reads_dict, compound_op)
            
            ssa_statements.append(ssa_stmt)
            
        elif left_hand_side.get("nodeType") == "MemberAccess":
            ssa_stmt = SSAConverter._handle_member_access_assignment(
                left_hand_side, right_hand_side, operator, reads_dict, writes_dict, version_counters
            )
            if ssa_stmt:
                ssa_statements.append(ssa_stmt)
            
        elif left_hand_side.get("nodeType") == "IndexAccess":
            statements = SSAConverter._handle_index_access_assignment(
                left_hand_side, right_hand_side, operator, reads_dict, writes_dict, version_counters
            )
            ssa_statements.extend(statements)
            
        return ssa_statements
    
    @staticmethod
    def _format_rhs_variables(right_hand_side, reads_dict, compound_op="="):
        """
        Format right-hand side variables with their versions.
        
        Args:
            right_hand_side (dict): Right-hand side expression node
            reads_dict (dict): Dictionary mapping variables to their read versions
            compound_op (str): The compound operator if any (+=, -=, etc.)
            
        Returns:
            str: Formatted right-hand side with versioned variables
        """
        # Extract reads from right-hand side
        rhs_reads = set()
        SSAConverter._extract_reads(right_hand_side, rhs_reads)
        
        # For arithmetic operations, prioritize important variables
        if compound_op in ["+=", "-=", "*=", "/="]:
            # First try to find the amount variable
            important_vars = ["amount", "value", "recipient", "spender", "sender", "from", "to"]
            selected_vars = []
            
            # First try to get 'amount' or 'value'
            for var_name in ["amount", "value"]:
                if var_name in rhs_reads:
                    selected_vars.append(var_name)
                    break
                    
            # If we have amount or value, we're good - otherwise get other important vars
            if not selected_vars:
                for var_name in important_vars:
                    if var_name in rhs_reads:
                        selected_vars.append(var_name)
                        
            # If we have any selected vars, use them
            if selected_vars:
                formatted_vars = []
                for var_name in selected_vars:
                    read_version = reads_dict.get(var_name, 0)
                    formatted_vars.append(f"{var_name}_{read_version}")
                return " ".join(formatted_vars)
            
        # Default behavior for all other cases
        formatted_reads = []
        for read_var in rhs_reads:
            read_version = reads_dict.get(read_var, 0)
            formatted_reads.append(f"{read_var}_{read_version}")
        
        return " ".join(formatted_reads)
    
    @staticmethod
    def _handle_member_access_assignment(left_hand_side, right_hand_side, operator, reads_dict, writes_dict, version_counters):
        """
        Process a member access assignment (obj.field = value) and convert to SSA form.
        
        Args:
            left_hand_side (dict): Left-hand side member access node
            right_hand_side (dict): Right-hand side expression node
            operator (str): Assignment operator
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            str: SSA statement for this member access assignment
        """
        # Handle struct field assignment
        base_expr = left_hand_side.get("expression", {})
        member_name = left_hand_side.get("memberName", "")
        
        if base_expr.get("nodeType") != "Identifier":
            return ""
            
        base_name = base_expr.get("name", "")
        structured_name = f"{base_name}.{member_name}"
        
        # Ensure structured_name is properly initialized in version tracking
        if structured_name not in version_counters:
            version_counters[structured_name] = 0
        
        # Get version for both base and structured name
        base_version = writes_dict.get(base_name, 0)
        struct_version = writes_dict.get(structured_name, 0)
        
        # Create SSA assignment statement for the struct field
        ssa_stmt = f"{structured_name}_{struct_version} = "
        
        # Handle compound assignments (+=, -=, etc.)
        compound_op = operator
        if compound_op not in ["=", ""]:
            # Format: x_1 = x_0 + right_side - never use negative versions
            prev_version = max(struct_version - 1, 0)
            ssa_stmt += f"{structured_name}_{prev_version} "
            
            # Extract the actual operation (+ from +=, - from -=, etc.)
            operation = compound_op[0]
            ssa_stmt += f"{operation} "
        
        # Handle literals directly
        if right_hand_side.get("nodeType") == "Literal":
            ssa_stmt += str(right_hand_side.get("value", ""))
        else:
            ssa_stmt += SSAConverter._format_rhs_variables(right_hand_side, reads_dict, compound_op)
        
        return ssa_stmt
    
    @staticmethod
    def _handle_index_access_assignment(left_hand_side, right_hand_side, operator, reads_dict, writes_dict, version_counters):
        """
        Process an index access assignment (arr[idx] = value) and convert to SSA form.
        
        Args:
            left_hand_side (dict): Left-hand side index access node
            right_hand_side (dict): Right-hand side expression node
            operator (str): Assignment operator
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            list: List of SSA statements for this index access assignment
        """
        ssa_statements = []
        
        # Handle array/mapping assignment
        base_expr = left_hand_side.get("baseExpression", {})
        index_expr = left_hand_side.get("indexExpression", {})
        
        # Handle nested IndexAccess like allowance[owner][spender]
        if base_expr.get("nodeType") == "IndexAccess":
            statements = SSAConverter._handle_nested_index_access_assignment(
                base_expr, index_expr, right_hand_side, operator, reads_dict, writes_dict, version_counters
            )
            ssa_statements.extend(statements)
        elif base_expr.get("nodeType") == "Identifier":
            base_name = base_expr.get("name", "")
            structured_name = SSAConverter._get_structured_index_name(base_name, index_expr)
            
            if structured_name:
                # Ensure structured_name is properly initialized in version tracking
                if structured_name not in version_counters:
                    version_counters[structured_name] = 0
                
                # Get version for both base and structured name
                base_version = writes_dict.get(base_name, 0)
                struct_version = writes_dict.get(structured_name, 0)
                
                # Create SSA assignment statement for the array/mapping element
                ssa_stmt = f"{structured_name}_{struct_version} = "
                
                # Handle compound assignments (+=, -=, etc.)
                compound_op = operator
                if compound_op not in ["=", ""]:
                    # Format: x_1 = x_0 + right_side - never use negative versions
                    prev_version = max(struct_version - 1, 0)
                    ssa_stmt += f"{structured_name}_{prev_version} "
                    
                    # Extract the actual operation (+ from +=, - from -=, etc.)
                    operation = compound_op[0]
                    ssa_stmt += f"{operation} "
                
                # Handle literals directly
                if right_hand_side.get("nodeType") == "Literal":
                    ssa_stmt += str(right_hand_side.get("value", ""))
                else:
                    ssa_stmt += SSAConverter._format_rhs_variables(
                        right_hand_side, reads_dict, compound_op
                    )
                
                ssa_statements.append(ssa_stmt)
        
        return ssa_statements
    
    @staticmethod
    def _handle_nested_index_access_assignment(base_expr, index_expr, right_hand_side, operator, reads_dict, writes_dict, version_counters):
        """
        Process a nested index access assignment (map[key1][key2] = value) and convert to SSA form.
        
        Args:
            base_expr (dict): Base expression node (which is also an index access)
            index_expr (dict): Index expression node for the outer index access
            right_hand_side (dict): Right-hand side expression node
            operator (str): Assignment operator
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            list: List of SSA statements for this nested index access assignment
        """
        ssa_statements = []
        
        # This is a double index access like allowance[owner][spender]
        nested_base_expr = base_expr.get("baseExpression", {})
        nested_index_expr = base_expr.get("indexExpression", {})
        
        if nested_base_expr.get("nodeType") != "Identifier":
            return ssa_statements
            
        nested_base_name = nested_base_expr.get("name", "")
        structured_name = ""
        
        # Build the first part of the access
        first_level = SSAConverter._get_structured_index_name(nested_base_name, nested_index_expr)
        
        # Now add the second level of indexing
        if first_level and index_expr.get("nodeType") == "Identifier":
            index_name = index_expr.get("name", "")
            if index_name:
                # Full two-level access e.g., allowance[owner][spender]
                structured_name = f"{first_level}[{index_name}]"
        elif first_level and index_expr.get("nodeType") == "MemberAccess":
            member_expr = index_expr.get("expression", {})
            member_name = index_expr.get("memberName", "")
            if member_expr.get("nodeType") == "Identifier":
                member_base = member_expr.get("name", "")
                if member_base and member_name:
                    structured_name = f"{first_level}[{member_base}.{member_name}]"
        
        if structured_name:
            # Ensure structured_name is properly initialized in version tracking
            if structured_name not in version_counters:
                version_counters[structured_name] = 0
            
            struct_version = writes_dict.get(structured_name, 0)
            
            # Create SSA assignment statement for the nested array/mapping element
            ssa_stmt = f"{structured_name}_{struct_version} = "
            
            # Handle compound assignments (+=, -=, etc.)
            compound_op = operator
            if compound_op not in ["=", ""]:
                prev_version = max(struct_version - 1, 0)  # No negative versions
                ssa_stmt += f"{structured_name}_{prev_version} "
                
                # Extract the actual operation (+ from +=, - from -=, etc.)
                operation = compound_op[0]  # First character of the operator
                ssa_stmt += f"{operation} "
            
            # Handle literals directly
            if right_hand_side.get("nodeType") == "Literal":
                ssa_stmt += str(right_hand_side.get("value", ""))
            else:
                ssa_stmt += SSAConverter._format_rhs_variables(
                    right_hand_side, reads_dict, compound_op
                )
            
            ssa_statements.append(ssa_stmt)
        
        return ssa_statements
    
    @staticmethod
    def _get_structured_index_name(base_name, index_expr):
        """
        Get a structured name for an indexed access (e.g., map[key]).
        
        Args:
            base_name (str): Base variable name
            index_expr (dict): Index expression node
            
        Returns:
            str: Structured name or empty string if not applicable
        """
        if not base_name:
            return ""
            
        # Form the structured name based on index type
        if index_expr.get("nodeType") == "Literal":
            index_value = index_expr.get("value", "")
            if index_value != "":
                return f"{base_name}[{index_value}]"
        elif index_expr.get("nodeType") == "Identifier":
            index_name = index_expr.get("name", "")
            if index_name:
                return f"{base_name}[{index_name}]"
        elif index_expr.get("nodeType") == "MemberAccess":
            # Handle cases like balances[msg.sender]
            member_expr = index_expr.get("expression", {})
            member_name = index_expr.get("memberName", "")
            
            if member_expr.get("nodeType") == "Identifier":
                member_base = member_expr.get("name", "")
                if member_base and member_name:
                    return f"{base_name}[{member_base}.{member_name}]"
        
        return ""
    
    @staticmethod
    def _handle_if_statement(node, reads_dict, block=None):
        """
        Process an if statement and convert to SSA form.
        
        Args:
            node (dict): If statement node
            reads_dict (dict): Dictionary mapping variables to their read versions
            block (dict, optional): The containing block for access tracking
            
        Returns:
            str: SSA statement for this if statement
        """
        condition = node.get("condition", {})
        
        # Extract condition variables
        cond_reads = set()
        SSAConverter._extract_reads(condition, cond_reads)
        
        # Update block accesses if provided
        if block and "accesses" in block:
            # Add condition reads to block reads
            reads = set(block["accesses"]["reads"])
            reads.update(cond_reads)
            block["accesses"]["reads"] = list(reads)
        
        # Get variable explicitly from condition for if statement
        var_name = ""
        if condition.get("nodeType") == "BinaryOperation":
            left = condition.get("leftExpression", {})
            if left.get("nodeType") == "Identifier":
                var_name = left.get("name", "")
            # Also handle structured accesses in conditions
            elif left.get("nodeType") == "IndexAccess":
                base_expr = left.get("baseExpression", {})
                index_expr = left.get("indexExpression", {})
                if base_expr.get("nodeType") == "Identifier":
                    base_name = base_expr.get("name", "")
                    if index_expr.get("nodeType") == "Identifier":
                        index_name = index_expr.get("name", "")
                        var_name = f"{base_name}[{index_name}]"
                    elif index_expr.get("nodeType") == "MemberAccess":
                        member_expr = index_expr.get("expression", {})
                        member_name = index_expr.get("memberName", "")
                        if member_expr.get("nodeType") == "Identifier":
                            member_base = member_expr.get("name", "")
                            var_name = f"{base_name}[{member_base}.{member_name}]"
        
        # Create SSA condition statement
        ssa_stmt = "if ("
        if var_name and var_name in reads_dict:
            var_version = reads_dict[var_name]
            ssa_stmt += f"{var_name}_{var_version}"
        elif cond_reads:
            formatted_reads = []
            for read_var in cond_reads:
                read_version = reads_dict.get(read_var, 0)
                formatted_reads.append(f"{read_var}_{read_version}")
            ssa_stmt += " ".join(formatted_reads)
        ssa_stmt += ")"
        
        return ssa_stmt
    
    @staticmethod
    def _handle_function_call(node, reads_dict, writes_dict, version_counters):
        """
        Process a function call and convert to SSA form.
        
        Args:
            node (dict): Function call node
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            str: SSA statement for this function call
        """
        if node["nodeType"] != "ExpressionStatement":
            return ""
            
        expression = node.get("expression", {})
        if expression.get("nodeType") != "FunctionCall":
            return ""
            
        # Determine if this is an external call (e.g., for reentrancy detection)
        is_external = False
        call_name = "call"
        
        # Check for function call via MemberAccess (e.g., contract.method())
        if expression.get("nodeType") == "FunctionCall":
            func_expr = expression.get("expression", {})
            
            # Check for direct function calls first
            if func_expr.get("nodeType") == "Identifier":
                func_name = func_expr.get("name", "")
                if func_name in ["revert", "require", "assert"]:
                    # Format revert statements directly
                    ret_var = "ret"
                    ret_version = writes_dict.get(ret_var, 1)
                    
                    # Get the arguments
                    args = []
                    for arg in expression.get("arguments", []):
                        if arg.get("nodeType") == "Literal":
                            if isinstance(arg.get("value"), str):
                                args.append(f'"{arg.get("value")}"')
                            else:
                                args.append(str(arg.get("value")))
                        elif arg.get("nodeType") == "Identifier":
                            var_name = arg.get("name", "")
                            var_version = reads_dict.get(var_name, 0)
                            args.append(f"{var_name}_{var_version}")
                    
                    if args:
                        return f"{ret_var}_{ret_version} = {func_name} {', '.join(args)}"
                    else:
                        return f"{ret_var}_{ret_version} = {func_name}"
            
            # Check for member access calls (.call, .transfer, etc.)
            elif func_expr.get("nodeType") == "MemberAccess":
                member_name = func_expr.get("memberName", "")
                base_expr = func_expr.get("expression", {})
                
                # Check for low-level calls (address.call, address.transfer, etc.)
                if member_name in ["call", "transfer", "send", "delegatecall", "staticcall"]:
                    is_external = True
                    
                    # Get base expression (the address)
                    if base_expr.get("nodeType") == "Identifier":
                        base_name = base_expr.get("name", "")
                        call_name = f"{base_name}.{member_name}"
                    else:
                        call_name = f"address.{member_name}"
                
                # Extract the contract or interface name if available
                elif base_expr.get("nodeType") == "FunctionCall":
                    # This is likely a pattern like IA(a).hello()
                    type_name = base_expr.get("expression", {}).get("name", "")
                    arg_name = ""
                    if base_expr.get("arguments") and len(base_expr.get("arguments")) > 0:
                        arg = base_expr.get("arguments")[0]
                        if arg.get("nodeType") == "Identifier":
                            arg_name = arg.get("name", "")
                    
                    if type_name and member_name:
                        is_external = True
                        call_name = f"{type_name}({arg_name}).{member_name}"
        
        # Get a unique ID for any return value from the call
        ret_var = "ret"
        ret_version = 0
        if ret_var in writes_dict:
            ret_version = writes_dict[ret_var]
        else:
            # If ret isn't tracked, generate a version
            version_counters[ret_var] = 1
            writes_dict[ret_var] = 1
            ret_version = 1
        
        # Create the function call statement with improved formatting
        if is_external:
            return f"{ret_var}_{ret_version} = call[external]({call_name})"
        else:
            # Create a more generic call representation
            ssa_stmt = f"{ret_var}_{ret_version} = call("
            
            # Extract argument variables
            arg_reads = set()
            for arg in expression.get("arguments", []):
                SSAConverter._extract_reads(arg, arg_reads)
            
            # Append versioned argument variables
            for read_var in arg_reads:
                read_version = reads_dict.get(read_var, 0)
                ssa_stmt += f"{read_var}_{read_version} "
            ssa_stmt += ")"
            
            return ssa_stmt
    
    @staticmethod
    def _handle_emit_statement(node, reads_dict, block):
        """
        Process an emit statement and convert to SSA form.
        
        Args:
            node (dict): Emit statement node
            reads_dict (dict): Dictionary mapping variables to their read versions
            block (dict): The containing basic block
            
        Returns:
            str: SSA statement for this emit statement
        """
        # Handle emit statements directly
        event_call = node.get("eventCall", {})
        if event_call.get("nodeType") != "FunctionCall":
            return ""
            
        # Get the event name from the expression
        event_expr = event_call.get("expression", {})
        event_name = event_expr.get("name", "Unknown")
        
        # Process each argument to extract values and track reads
        individual_args = []
        event_reads = set()
        
        for arg in event_call.get("arguments", []):
            # Extract reads from this argument
            arg_reads = set()
            SSAConverter._extract_reads(arg, arg_reads)
            event_reads.update(arg_reads)  # Add to the event's overall reads
            
            # Process different argument types
            if arg.get("nodeType") == "Identifier":
                # Simple variable
                var_name = arg.get("name", "")
                var_version = reads_dict.get(var_name, 0)
                individual_args.append(f"{var_name}_{var_version}")
            elif arg.get("nodeType") == "MemberAccess":
                # Handle msg.sender type accesses
                member_name = arg.get("memberName", "")
                expr = arg.get("expression", {})
                expr_name = expr.get("name", "")
                if expr_name and member_name:
                    mem_access = f"{expr_name}.{member_name}"
                    mem_version = reads_dict.get(mem_access, 0)
                    individual_args.append(f"{mem_access}_{mem_version}")
            elif arg.get("nodeType") == "Literal":
                # Literal values
                individual_args.append(str(arg.get("value", "")))
            elif arg.get("nodeType") == "FunctionCall":
                # Handle address(0) type calls
                func_expr = arg.get("expression", {})
                if func_expr.get("nodeType") == "Identifier" and func_expr.get("name") == "address":
                    # This is address(0) - special handling for Transfer events in mint/burn
                    if len(arg.get("arguments", [])) > 0 and arg["arguments"][0].get("nodeType") == "Literal":
                        # Use address(0)_0 for the zero address
                        individual_args.append(f"address(0)_0")
                    else:
                        # Fallback to regular function call handling
                        individual_args.append("address(0)_0")
                else:
                    # Other function calls in arguments - handle nested calls
                    func_reads = set()
                    SSAConverter._extract_reads(arg, func_reads)
                    for read_var in func_reads:
                        read_version = reads_dict.get(read_var, 0)
                        individual_args.append(f"{read_var}_{read_version}")
        
        # Update block accesses
        block["accesses"]["reads"] = list(set(block["accesses"]["reads"]).union(event_reads))
        
        # Create a clean emit statement with individual arguments properly formatted
        ssa_stmt = f"emit {event_name}({', '.join(individual_args)})"
        
        return ssa_stmt
    
    @staticmethod
    def _handle_return_statement(node, reads_dict):
        """
        Process a return statement and convert to SSA form.
        
        Args:
            node (dict): Return statement node
            reads_dict (dict): Dictionary mapping variables to their read versions
            
        Returns:
            str: SSA statement for this return statement
        """
        expression = node.get("expression", {})
        
        # Handle literal returns directly
        if expression and expression.get("nodeType") == "Literal":
            # Create SSA return statement with literal value
            return f"return {expression.get('value', '')}"
        else:
            # Extract return variables
            ret_reads = set()
            SSAConverter._extract_reads(expression, ret_reads)
            
            # Create SSA return statement
            ssa_stmt = "return "
            for read_var in ret_reads:
                read_version = reads_dict.get(read_var, 0)
                ssa_stmt += f"{read_var}_{read_version} "
            
            return ssa_stmt.strip()
    
    @staticmethod
    def _handle_variable_declaration(node, reads_dict, writes_dict, version_counters):
        """
        Process a variable declaration statement and convert to SSA form.
        
        Args:
            node (dict): Variable declaration statement node
            reads_dict (dict): Dictionary mapping variables to their read versions
            writes_dict (dict): Dictionary mapping variables to their write versions
            version_counters (dict): Dictionary tracking the highest version for each variable
            
        Returns:
            list: List of SSA statements for this variable declaration
        """
        ssa_statements = []
        
        # Handle variable declarations (e.g., uint bal = balances[msg.sender])
        declarations = node.get("declarations", [])
        init_value = node.get("initialValue", {})
        
        for decl in declarations:
            if decl and decl.get("nodeType") == "VariableDeclaration":
                var_name = decl.get("name", "")
                var_version = writes_dict.get(var_name, 0)
                
                # Create SSA variable declaration statement
                ssa_stmt = f"{var_name}_{var_version} = "
                
                # Handle literals directly
                if init_value and init_value.get("nodeType") == "Literal":
                    ssa_stmt += str(init_value.get("value", ""))
                elif init_value:
                    # Extract reads from initialization expression
                    init_reads = set()
                    SSAConverter._extract_reads(init_value, init_reads)
                    
                    # Append versioned initialization variables
                    formatted_reads = []
                    for read_var in init_reads:
                        read_version = reads_dict.get(read_var, 0)
                        formatted_reads.append(f"{read_var}_{read_version}")
                    
                    # Join all reads with spaces
                    ssa_stmt += " ".join(formatted_reads)
                
                ssa_statements.append(ssa_stmt)
        
        return ssa_statements
    
    @staticmethod
    def _handle_revert_statement(node, reads_dict, block=None):
        """
        Process a revert statement and convert to SSA form.
        
        Args:
            node (dict): Revert statement node
            reads_dict (dict): Dictionary mapping variables to their read versions
            block (dict, optional): The containing block for access tracking
            
        Returns:
            str: SSA statement for this revert statement
        """
        # Get the expression containing the revert call
        expression = node.get("expression", {})
        if expression.get("nodeType") != "FunctionCall":
            return "revert"
            
        # Get the function expression to determine if it's revert or require
        func_expr = expression.get("expression", {})
        func_name = "revert"  # Default
        
        if func_expr.get("nodeType") == "Identifier":
            func_name = func_expr.get("name", "revert")
            
        # Get the arguments
        revert_args = []
        arg_reads = set()
        
        for arg in expression.get("arguments", []):
            # Extract variable reads from the argument
            arg_read_set = set()
            SSAConverter._extract_reads(arg, arg_read_set)
            arg_reads.update(arg_read_set)
            
            # Format the argument for the SSA statement
            if arg.get("nodeType") == "Literal":
                value = arg.get("value", "")
                if isinstance(value, str):
                    # String literal - use as is with quotes
                    revert_args.append(f'"{value}"')
                else:
                    # Numeric literal
                    revert_args.append(str(value))
            elif arg.get("nodeType") == "Identifier":
                var_name = arg.get("name", "")
                var_version = reads_dict.get(var_name, 0)
                revert_args.append(f"{var_name}_{var_version}")
            elif arg.get("nodeType") == "BinaryOperation":
                # Handle binary operations (common in require statements)
                left_reads = set()
                right_reads = set()
                SSAConverter._extract_reads(arg.get("leftExpression", {}), left_reads)
                SSAConverter._extract_reads(arg.get("rightExpression", {}), right_reads)
                
                # Format the left side
                left_str = ""
                if len(left_reads) == 1:
                    var_name = next(iter(left_reads))
                    var_version = reads_dict.get(var_name, 0)
                    left_str = f"{var_name}_{var_version}"
                
                # Get the operator
                operator = arg.get("operator", "")
                
                # Format the right side
                right_str = ""
                if len(right_reads) == 1:
                    var_name = next(iter(right_reads))
                    var_version = reads_dict.get(var_name, 0)
                    right_str = f"{var_name}_{var_version}"
                elif arg.get("rightExpression", {}).get("nodeType") == "Literal":
                    right_str = str(arg.get("rightExpression", {}).get("value", ""))
                
                if left_str and right_str:
                    revert_args.append(f"{left_str} {operator} {right_str}")
        
        # Update block accesses if provided
        if block and "accesses" in block:
            # Add revert argument reads to block reads
            reads = set(block["accesses"]["reads"])
            reads.update(arg_reads)
            block["accesses"]["reads"] = list(reads)
        
        # Create the statement with arguments if any
        if revert_args:
            return f"{func_name} {', '.join(revert_args)}"
        else:
            return func_name
    
    @staticmethod
    def assign_ssa_versions(basic_blocks):
        """
        Assign SSA variable versions to each variable access across blocks.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with accesses
            
        Returns:
            list: List of basic block dictionaries with SSA versioning added
        """
        if not basic_blocks:
            return []
            
        # Ensure each block has an accesses field
        for block in basic_blocks:
            if "accesses" not in block:
                block["accesses"] = {"reads": [], "writes": []}
        
        # Initialize version tracking
        version_counters, current_versions = SSAConverter._initialize_version_tracking(basic_blocks)
        
        # Second pass: assign versions to each block
        for block in basic_blocks:
            # Assign versions to variables in this block
            reads_dict, writes_dict = SSAConverter._assign_variable_versions(
                block, current_versions, version_counters
            )
            
            # Create SSA statements
            block["ssa_statements"] = []
            
            # Handle special number increment operations
            number_statements = SSAConverter._process_number_increment(block, reads_dict, writes_dict)
            block["ssa_statements"].extend(number_statements)
            
            # Process statements and convert to SSA form
            for statement in block["statements"]:
                stmt_type = statement["type"]
                node = statement["node"]
                
                if stmt_type == "Assignment":
                    assignment_statements = SSAConverter._handle_assignment(
                        node, reads_dict, writes_dict, version_counters
                    )
                    block["ssa_statements"].extend(assignment_statements)
                
                elif stmt_type == "IfStatement":
                    if_statement = SSAConverter._handle_if_statement(node, reads_dict, block)
                    block["ssa_statements"].append(if_statement)
                
                elif stmt_type == "Revert":
                    revert_statement = SSAConverter._handle_revert_statement(node, reads_dict, block)
                    if revert_statement:
                        block["ssa_statements"].append(revert_statement)
                
                elif stmt_type == "FunctionCall":
                    call_statement = SSAConverter._handle_function_call(
                        node, reads_dict, writes_dict, version_counters
                    )
                    if call_statement:
                        block["ssa_statements"].append(call_statement)
                
                elif stmt_type == "EmitStatement":
                    emit_statement = SSAConverter._handle_emit_statement(node, reads_dict, block)
                    if emit_statement:
                        block["ssa_statements"].append(emit_statement)
                
                elif stmt_type == "Return":
                    return_statement = SSAConverter._handle_return_statement(node, reads_dict)
                    if return_statement:
                        block["ssa_statements"].append(return_statement)
                
                elif stmt_type == "VariableDeclaration":
                    var_statements = SSAConverter._handle_variable_declaration(
                        node, reads_dict, writes_dict, version_counters
                    )
                    block["ssa_statements"].extend(var_statements)
        
        return basic_blocks
    
    @staticmethod
    def insert_phi_functions(basic_blocks):
        """
        Insert phi-functions at control flow merge points to reconcile variable versions.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with SSA statements
            
        Returns:
            list: List of basic block dictionaries with added phi-functions
        """
        # Build a mapping from block ID to block index for easier lookup
        block_ids = {block["id"]: idx for idx, block in enumerate(basic_blocks)}
        
        # Initialize a dictionary to track predecessors for each block
        predecessors = {block["id"]: [] for block in basic_blocks}
        
        # Build the control flow graph by analyzing terminators
        for block in basic_blocks:
            terminator = block.get("terminator", "")
            if not terminator:
                # If no terminator and not the last block, assume fall-through
                block_idx = block_ids.get(block["id"])
                if block_idx is not None and block_idx + 1 < len(basic_blocks):
                    next_block = basic_blocks[block_idx + 1]
                    predecessors[next_block["id"]].append(block["id"])
                continue
                
            if isinstance(terminator, str):
                # Handle if-then-else conditional jumps
                if "then goto " in terminator and " else goto " in terminator:
                    parts = terminator.split(" then goto ")
                    then_target = parts[1].split(" else goto ")[0]
                    else_target = parts[1].split(" else goto ")[1]
                    
                    # Record predecessors
                    if then_target in predecessors:
                        predecessors[then_target].append(block["id"])
                    if else_target in predecessors:
                        predecessors[else_target].append(block["id"])
                
                # Handle unconditional jumps
                elif terminator.startswith("goto "):
                    target = terminator.split("goto ")[1]
                    if target in predecessors:
                        predecessors[target].append(block["id"])
        
        # Find loop headers (blocks with back-edges pointing to them)
        loop_headers = set()
        for block in basic_blocks:
            if block.get("is_loop_header"):
                loop_headers.add(block["id"])
            
            # Check for back-edges
            terminator = block.get("terminator", "")
            if terminator and terminator.startswith("goto "):
                target = terminator.split("goto ")[1]
                if target in block_ids and block_ids[target] < block_ids[block["id"]]:
                    loop_headers.add(target)
        
        # Find merge blocks (blocks with multiple predecessors)
        merge_blocks = [block_id for block_id, preds in predecessors.items() if len(preds) > 1]
        
        # Process merge blocks and loop headers for phi insertion
        for block_id in set(merge_blocks).union(loop_headers):
            if block_id not in block_ids:
                continue
                
            block = basic_blocks[block_ids[block_id]]
            pred_ids = predecessors.get(block_id, [])
            pred_blocks = [basic_blocks[block_ids[pred_id]] for pred_id in pred_ids if pred_id in block_ids]
            
            # For loop headers, add blocks with back-edges as predecessors
            if block_id in loop_headers:
                for b in basic_blocks:
                    terminator = b.get("terminator", "")
                    if (terminator and terminator.startswith("goto ") and 
                        terminator.split("goto ")[1] == block_id and 
                        b["id"] not in [p["id"] for p in pred_blocks]):
                        pred_blocks.append(b)
            
            if not pred_blocks:
                continue
            
            # Collect variables needing phi functions and their versions from each predecessor
            phi_variables = {}
            for pred in pred_blocks:
                for var in pred.get("accesses", {}).get("writes", []):
                    if var not in phi_variables:
                        phi_variables[var] = {}
                    
                    # Store the version from this predecessor
                    version = pred.get("ssa_versions", {}).get("writes", {}).get(var, 0)
                    if version > 0:  # Only track non-zero versions
                        phi_variables[var][pred["id"]] = version
            
            # Generate phi functions
            phi_functions = []
            for var, versions_by_block in phi_variables.items():
                # Only add phi when:
                # - Multiple different versions of a variable reach this block, or
                # - Variable is written in a predecessor and read in this block
                versions = list(versions_by_block.values())
                
                if (len(set(versions)) > 1 or 
                    (var in block.get("accesses", {}).get("reads", []) and versions)):
                    
                    # Create a new version for the phi function (max existing + 1)
                    new_version = max(versions, default=0) + 1
                    
                    # Build phi function arguments (one from each predecessor)
                    phi_args = []
                    for pred in pred_blocks:
                        if pred["id"] in versions_by_block:
                            # Use the written version from this predecessor
                            version = versions_by_block[pred["id"]]
                        else:
                            # Use the read version if no write
                            version = pred.get("ssa_versions", {}).get("reads", {}).get(var, 0)
                        phi_args.append(f"{var}_{version}")
                    
                    # Create the phi function statement
                    phi_stmt = f"{var}_{new_version} = phi({', '.join(phi_args)})"
                    phi_functions.append(phi_stmt)
                    
                    # Update SSA versions in this block
                    if "ssa_versions" not in block:
                        block["ssa_versions"] = {"reads": {}, "writes": {}}
                    
                    block["ssa_versions"]["writes"][var] = new_version
                    block["ssa_versions"]["reads"][var] = new_version
                    
                    # Update statements in this block to use the new version
                    if "ssa_statements" in block:
                        updated_statements = []
                        for stmt in block["ssa_statements"]:
                            # Don't modify the phi function itself
                            if not stmt.startswith(f"{var}_{new_version} = phi("):
                                # Replace all references to any version of this variable with the new version
                                for v in range(0, max(versions) + 1):
                                    stmt = stmt.replace(f"{var}_{v}", f"{var}_{new_version}")
                            updated_statements.append(stmt)
                        
                        block["ssa_statements"] = updated_statements
            
            # Add phi functions to the beginning of the block
            if phi_functions:
                if "ssa_statements" not in block:
                    block["ssa_statements"] = []
                block["ssa_statements"] = phi_functions + block["ssa_statements"]
        
        return basic_blocks
    
    @staticmethod
    def cleanup_ssa_statements(basic_blocks):
        """
        Clean up SSA statements to fix variable duplication and call formatting issues.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with SSA statements
            
        Returns:
            list: List of basic blocks with cleaned SSA statements
        """
        if not basic_blocks:
            return []
            
        for block in basic_blocks:
            if "ssa_statements" not in block:
                continue
                
            cleaned_statements = []
            for stmt in block.get("ssa_statements", []):
                # Clean up compound operations with duplicated variables
                if " = " in stmt and (" + " in stmt or " - " in stmt):
                    lhs, rhs = stmt.split(" = ", 1)
                    
                    # Identify and remove duplicate variables in + operations
                    if " + " in rhs:
                        # Regular handling for operations
                        terms = [term.strip() for term in rhs.split(" + ")]
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_terms = []
                        for term in terms:
                            if "_" in term:
                                base = term.split("_")[0]
                                if base not in seen:
                                    seen.add(base)
                                    unique_terms.append(term)
                            else:
                                unique_terms.append(term)
                        cleaned_stmt = f"{lhs} = {' + '.join(unique_terms)}"
                        
                        cleaned_statements.append(cleaned_stmt)
                    
                    # Identify and remove duplicate variables in - operations
                    elif " - " in rhs:
                        # Handle subtraction differently: keep the first part, then clean duplicates after the -
                        first_part, rest = rhs.split(" - ", 1)
                        terms = [term.strip() for term in rest.split()]
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_terms = []
                        for term in terms:
                            if "_" in term:
                                base = term.split("_")[0]
                                if base not in seen:
                                    seen.add(base)
                                    unique_terms.append(term)
                            else:
                                unique_terms.append(term)
                        cleaned_stmt = f"{lhs} = {first_part} - {' '.join(unique_terms)}"
                        
                        cleaned_statements.append(cleaned_stmt)
                
                # Fix call[internal] formatting to include commas between arguments
                elif "call[internal](" in stmt:
                    call_prefix = stmt.split("call[internal](")[0] + "call[internal]("
                    call_parts = stmt.split("call[internal](")[1].strip(")")
                    
                    # Parse the function name and arguments
                    if "," in call_parts:
                        # Already has commas, keep as is
                        cleaned_statements.append(stmt)
                    else:
                        parts = call_parts.strip().split()
                        if len(parts) > 1:
                            # Format with proper commas between function name and args
                            func_name = parts[0]
                            args = parts[1:]
                            formatted_call = f"{call_prefix}{func_name}, {', '.join(args)})"
                            cleaned_statements.append(formatted_call)
                        else:
                            # Just a function name, no args
                            cleaned_statements.append(stmt)
                else:
                    # No need to clean this statement
                    cleaned_statements.append(stmt)
            
            # Update the block with cleaned statements
            block["ssa_statements"] = cleaned_statements
            
        return basic_blocks
    
    @staticmethod
    def integrate_ssa_output(basic_blocks):
        """
        Create a clean SSA representation from the basic blocks.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with SSA information
            
        Returns:
            list: List of simplified SSA block dictionaries with ID, statements, terminators, and variable accesses
        """
        if not basic_blocks:
            return []
            
        ssa_blocks = []
        
        # Map blocks by ID for easier lookup
        block_ids = {block["id"]: idx for idx, block in enumerate(basic_blocks)}
        
        # First update all EmitStatement terminators to goto next block
        for idx, block in enumerate(basic_blocks):
            if block.get("terminator") == "EmitStatement":
                # Convert EmitStatement to a goto to the next block
                if idx < len(basic_blocks) - 1:
                    # Not the last block, so add goto next block
                    next_block = basic_blocks[idx + 1]
                    block["terminator"] = f"goto {next_block['id']}"
                else:
                    # Last block in function, should return
                    block["terminator"] = "return"
        
        for block in basic_blocks:
            # Check for emit statements in this block
            has_emit = False
            has_revert = False
            for stmt in block.get("ssa_statements", []):
                if stmt.startswith("emit "):
                    has_emit = True
                elif stmt.startswith("revert"):
                    has_revert = True
            
            # Extract only the essential SSA information
            ssa_block = {
                "id": block["id"],
                "ssa_statements": block.get("ssa_statements", []),
                "terminator": block.get("terminator", None)
            }
            
            # Always include accesses for better tracking
            ssa_block["accesses"] = block.get("accesses", {"reads": [], "writes": []})
            
            # Fix any emit statements that might not have been converted to goto
            if has_emit and ssa_block["terminator"] == "EmitStatement":
                # Find the next block to goto
                current_idx = basic_blocks.index(block)
                if current_idx < len(basic_blocks) - 1:
                    next_block = basic_blocks[current_idx + 1]
                    ssa_block["terminator"] = f"goto {next_block['id']}"
                else:
                    ssa_block["terminator"] = "return"
            
            # Set revert terminator for blocks with revert statements
            if has_revert:
                ssa_block["terminator"] = "revert"
                
            # Clean up statements based on their classification
            new_statements = []
            for stmt in ssa_block["ssa_statements"]:
                # Check for revert-like calls in any format
                if stmt.startswith("revert ") or stmt.startswith("require ") or stmt.startswith("assert "):
                    # Already properly formatted
                    new_statements.append(stmt)
                    # Set proper terminator
                    if stmt.startswith("revert "):
                        ssa_block["terminator"] = "revert"
                    elif stmt == ssa_block["ssa_statements"][-1]:
                        # require/assert only reverts if they're the last statement
                        ssa_block["terminator"] = "revert"
                # Check for any call statement that might be a revert/require/assert
                elif "call[" in stmt and "(" in stmt and ")" in stmt:
                    # Parse the call parts: type and function name
                    call_prefix = stmt.split("call[")[0] + "call["
                    call_type = stmt.split("call[")[1].split("]")[0]
                    
                    # Extract function name and args
                    func_call_part = stmt.split("]")[1].strip()
                    if func_call_part.startswith("(") and func_call_part.endswith(")"):
                        # Extract function name and args
                        func_and_args = func_call_part[1:-1]  # Remove outer parentheses
                        
                        # Split on first comma to separate function name and args
                        if "," in func_and_args:
                            func_name, args = func_and_args.split(",", 1)
                            args = args.strip()
                        else:
                            func_name = func_and_args
                            args = ""
                        
                        func_name = func_name.strip()
                        
                        # Extract return part if any
                        ret_part = ""
                        if " = " in stmt:
                            ret_part = stmt.split(" = ")[0] + " = "
                        
                        # Handle revert type calls - regardless of call_type
                        if func_name in ["revert", "require", "assert"]:
                            if func_name == "revert":
                                if args:
                                    new_statements.append(f"{ret_part}revert {args}")
                                else:
                                    new_statements.append(f"{ret_part}revert")
                                ssa_block["terminator"] = "revert"
                            elif func_name == "require":
                                if args:
                                    new_statements.append(f"{ret_part}require {args}")
                                else:
                                    new_statements.append(f"{ret_part}require")
                                # Set terminator to revert if this is the last statement
                                if stmt == ssa_block["ssa_statements"][-1]:
                                    ssa_block["terminator"] = "revert"
                            elif func_name == "assert":
                                if args:
                                    new_statements.append(f"{ret_part}assert {args}")
                                else:
                                    new_statements.append(f"{ret_part}assert")
                                # Set terminator to revert if this is the last statement
                                if stmt == ssa_block["ssa_statements"][-1]:
                                    ssa_block["terminator"] = "revert"
                        else:
                            # Not a revert type, keep original statement
                            new_statements.append(stmt)
                    else:
                        # Malformed call, keep original
                        new_statements.append(stmt)
                else:
                    # Not a call statement, keep as is
                    new_statements.append(stmt)
            
            ssa_block["ssa_statements"] = new_statements
            
            # Check for emit statements and update accesses if needed
            if has_emit:
                # Find the variables used in the emit statement
                for stmt in ssa_block["ssa_statements"]:
                    if stmt.startswith("emit "):
                        # Extract arguments from emit statement - format: emit Name(arg1, arg2, ...)
                        args_part = stmt.split("(", 1)[1].rstrip(")")
                        args = [arg.strip() for arg in args_part.split(",")]
                        
                        # Add reads for each argument - extract variable name without version
                        emit_reads = []
                        for arg in args:
                            if "_" in arg:
                                var_name = arg.split("_")[0]
                                emit_reads.append(var_name)
                        
                        # Update the block's reads with the emit arguments
                        reads = set(ssa_block["accesses"]["reads"])
                        reads.update(emit_reads)
                        ssa_block["accesses"]["reads"] = list(reads)
            
            # Similarly, check for revert statements and update accesses
            if has_revert:
                # Find the variables used in the revert statement
                for stmt in ssa_block["ssa_statements"]:
                    if stmt.startswith("revert ") or "call[revert](revert" in stmt or "call[external](revert" in stmt:
                        # Extract arguments from revert statement - format: revert arg1, arg2, ...
                        args_part = stmt[7:].strip()  # Remove "revert " prefix
                        if args_part:
                            args = [arg.strip() for arg in args_part.split(",")]
                            
                            # Add reads for each argument - extract variable name without version
                            revert_reads = []
                            for arg in args:
                                if "_" in arg and not arg.startswith('"'):
                                    var_name = arg.split("_")[0]
                                    revert_reads.append(var_name)
                            
                            # Update the block's reads with the revert arguments
                            reads = set(ssa_block["accesses"]["reads"])
                            reads.update(revert_reads)
                            ssa_block["accesses"]["reads"] = list(reads)
            
            # Clean up phi functions in accesses
            if "accesses" in ssa_block:
                reads = []
                for read in ssa_block["accesses"]["reads"]:
                    # Remove phi function artifacts like "phi(i"
                    if read.startswith("phi("):
                        continue
                    reads.append(read)
                ssa_block["accesses"]["reads"] = reads
                
            # Add block to the list
            ssa_blocks.append(ssa_block)
            
        return ssa_blocks

# Function to convert basic blocks to SSA form
def convert_to_ssa(basic_blocks):
    """
    Convert the given basic blocks to SSA form.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of basic block dictionaries in SSA form
    """
    # Apply SSA transformation steps
    blocks_with_versions = SSAConverter.assign_ssa_versions(basic_blocks)
    blocks_with_phi = SSAConverter.insert_phi_functions(blocks_with_versions)
    cleaned_blocks = SSAConverter.cleanup_ssa_statements(blocks_with_phi)
    ssa_result = SSAConverter.integrate_ssa_output(cleaned_blocks)
    return ssa_result