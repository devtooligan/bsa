"""
Control flow functionality for BSA.
"""

from bsa.parser.basic_blocks import get_statement_type

class ControlFlowRefiner:
    """
    Handles refinement of basic blocks to handle control flow structures.
    """
    
    @staticmethod
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
            if isinstance(block.get("terminator"), str) and (
                "goto" in block["terminator"] or 
                block["terminator"] in ["return", "revert", "require", "assert"]
            ):
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
            
            # Handle revert/require/assert statements - all of these should be true terminators
            if block.get("terminator") in ["Revert", "Require", "Assert"]:
                # Update the terminator to the corresponding explicit value
                term_type = block.get("terminator").lower()
                block["terminator"] = term_type
                # Don't add a goto after these - they're true terminators
                continue
            
            # Handle any blocks with revert-like statements in their SSA representation
            if "ssa_statements" in block:
                handled = False
                for stmt in block.get("ssa_statements", []):
                    if stmt.startswith("revert ") or stmt == "revert":
                        block["terminator"] = "revert"
                        handled = True
                        break
                    elif stmt.startswith("require "):
                        # Format: require inputValue_0 < 100
                        # Preserve the entire condition in the terminator
                        parts = stmt.split(" ", 1)
                        if len(parts) > 1:
                            binary_condition = parts[1]
                            block["terminator"] = f"require {binary_condition}"
                        else:
                            block["terminator"] = "require"
                        handled = True
                        break
                    elif stmt == "require":
                        block["terminator"] = "require"
                        handled = True
                        break
                    elif stmt.startswith("assert "):
                        # Format: assert inputValue_0 != 50
                        # Preserve the entire condition in the terminator
                        parts = stmt.split(" ", 1)
                        if len(parts) > 1:
                            binary_condition = parts[1]
                            block["terminator"] = f"assert {binary_condition}"
                        else:
                            block["terminator"] = "assert"
                        handled = True
                        break
                    elif stmt == "assert":
                        block["terminator"] = "assert"
                        handled = True
                        break
                
                if handled:
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
                continue
                
            # Check if this is an empty block that we can optimize out
            if len(block.get("statements", [])) == 0 and len(block.get("ssa_statements", [])) == 0:
                # This is an empty block - see if we can optimize it by making the previous block
                # go directly to where this block would go
                if idx < len(basic_blocks) - 1:
                    # There's a next block we can go to
                    next_block = basic_blocks[idx + 1]
                    
                    # If the next block has a revert/require/assert, preserve that terminator type
                    if next_block.get("terminator") in ["revert", "require", "assert"]:
                        block["terminator"] = next_block.get("terminator")
                    else:
                        block["terminator"] = f"goto {next_block['id']}"
                    
                    # Look for blocks pointing to this empty block and update them
                    for prev_idx, prev_block in enumerate(basic_blocks):
                        term = prev_block.get("terminator", "")
                        # Handle both regular goto and if-then-else goto patterns
                        if isinstance(term, str) and f"goto {block['id']}" in term:
                            # Special case for if statement handling
                            if "if " in term and " then goto " in term and " else goto " in term:
                                # Only redirect the relevant part of the if statement
                                if f"then goto {block['id']}" in term and f"else goto {block['id']}" in term:
                                    # Both branches go to this empty block, can completely replace with simple goto
                                    if next_block.get("terminator") in ["revert", "require", "assert"]:
                                        prev_block["terminator"] = next_block.get("terminator")
                                    else:
                                        prev_block["terminator"] = f"goto {next_block['id']}"
                                elif f"then goto {block['id']}" in term:
                                    # Only the 'then' branch, keep the else as is
                                    parts = term.split(" then goto ")
                                    condition = parts[0]
                                    else_part = parts[1].split(" else goto ")[1]
                                    prev_block["terminator"] = f"{condition} then goto {next_block['id']} else goto {else_part}"
                                elif f"else goto {block['id']}" in term:
                                    # Only the 'else' branch, keep the then as is
                                    parts = term.split(" then goto ")
                                    condition = parts[0]
                                    then_part = parts[1].split(" else goto ")[0]
                                    prev_block["terminator"] = f"{condition} then goto {then_part} else goto {next_block['id']}"
                            else:
                                # Simple goto replacement
                                prev_block["terminator"] = term.replace(
                                    f"goto {block['id']}", f"goto {next_block['id']}")
                else:
                    # Last block in function, should return
                    block["terminator"] = "return"
                continue
            
            # For all other blocks, determine if they should goto next block or return
            if idx < len(basic_blocks) - 1:
                # Not the last block, so add goto next block
                next_block = basic_blocks[idx + 1]
                block["terminator"] = f"goto {next_block['id']}"
            else:
                # Last block in function, should return
                block["terminator"] = "return"
        
        return basic_blocks
    
    @staticmethod
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
            
        refiner = ControlFlowRefiner()
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
                
            # Handle based on control flow type
            if has_if:
                new_blocks, block_counter = refiner._handle_if_statement(
                    block, block_idx, block_counter, basic_blocks
                )
                refined_blocks.extend(new_blocks)
            elif has_for_loop:
                new_blocks, block_counter = refiner._handle_for_loop(
                    block, block_idx, block_counter, basic_blocks
                )
                refined_blocks.extend(new_blocks)
            elif has_while_loop:
                new_blocks, block_counter = refiner._handle_while_loop(
                    block, block_idx, block_counter, basic_blocks
                )
                refined_blocks.extend(new_blocks)
        
        return refined_blocks
    
    def _handle_if_statement(self, block, block_idx, block_counter, basic_blocks):
        """
        Process an if statement block into conditional and branch blocks.
        
        Args:
            block (dict): The basic block containing an if statement
            block_idx (int): Index of this block in the original list
            block_counter (int): Counter for generating new block IDs
            basic_blocks (list): Complete list of basic blocks
            
        Returns:
            tuple: (new_blocks, updated_block_counter)
        """
        new_blocks = []
        
        # Find the index of the IfStatement
        if_idx = None
        for idx, statement in enumerate(block["statements"]):
            if statement["type"] == "IfStatement":
                if_idx = idx
                break
        
        # Extract the if statement and its condition
        if_statement = block["statements"][if_idx]
        condition = if_statement["node"].get("condition", {})
        
        # Extract condition variables for accesses tracking
        condition_reads = set()
        if condition.get("nodeType") == "BinaryOperation":
            left_expr = condition.get("leftExpression", {})
            right_expr = condition.get("rightExpression", {})
            
            # Process left expression
            if left_expr.get("nodeType") == "Identifier":
                condition_reads.add(left_expr.get("name", ""))
            
            # Process right expression
            if right_expr.get("nodeType") == "Identifier":
                condition_reads.add(right_expr.get("name", ""))
        
        # Extract statements before the if
        pre_if_statements = block["statements"][:if_idx]
        
        # Create a conditional block with the if statement
        conditional_block = {
            "id": block["id"],
            "statements": pre_if_statements + [if_statement],
            "terminator": "conditional",
            "accesses": {
                "reads": list(condition_reads),
                "writes": []
            }
        }
        
        # Create true branch block
        true_block_id = f"Block{block_counter}"
        block_counter += 1
        
        true_body = if_statement["node"].get("trueBody", {})
        true_statements = true_body.get("statements", [])
        true_typed_statements = self._get_typed_statements(true_statements)
        
        # Check if the true branch contains a revert statement
        contains_revert = False
        true_reads = set()
        true_writes = set()
        for stmt in true_typed_statements:
            if stmt["type"] == "Revert":
                contains_revert = True
                # Extract revert arguments for access tracking
                if stmt["node"].get("expression", {}).get("nodeType") == "FunctionCall":
                    func_expr = stmt["node"].get("expression", {})
                    for arg in func_expr.get("arguments", []):
                        if arg.get("nodeType") == "Identifier":
                            true_reads.add(arg.get("name", ""))
                        elif arg.get("nodeType") == "BinaryOperation":
                            left = arg.get("leftExpression", {})
                            right = arg.get("rightExpression", {})
                            if left.get("nodeType") == "Identifier":
                                true_reads.add(left.get("name", ""))
                            if right.get("nodeType") == "Identifier":
                                true_reads.add(right.get("name", ""))
                break
        
        true_block = {
            "id": true_block_id,
            "statements": true_typed_statements,
            "terminator": "revert" if contains_revert else None,
            "branch_type": "true",
            "accesses": {
                "reads": list(true_reads),
                "writes": list(true_writes)
            }
        }
        
        # Create false branch block
        false_block_id = f"Block{block_counter}"
        block_counter += 1
        
        false_body = if_statement["node"].get("falseBody", {})
        false_statements = false_body.get("statements", []) if false_body else []
        false_typed_statements = self._get_typed_statements(false_statements)
        
        # Check if the false branch contains a revert
        false_has_revert = False
        false_reads = set()
        false_writes = set()
        for stmt in false_typed_statements:
            if stmt["type"] == "Revert":
                false_has_revert = True
                # Extract revert arguments for access tracking
                if stmt["node"].get("expression", {}).get("nodeType") == "FunctionCall":
                    func_expr = stmt["node"].get("expression", {})
                    for arg in func_expr.get("arguments", []):
                        if arg.get("nodeType") == "Identifier":
                            false_reads.add(arg.get("name", ""))
                        elif arg.get("nodeType") == "BinaryOperation":
                            left = arg.get("leftExpression", {})
                            right = arg.get("rightExpression", {})
                            if left.get("nodeType") == "Identifier":
                                false_reads.add(left.get("name", ""))
                            if right.get("nodeType") == "Identifier":
                                false_reads.add(right.get("name", ""))
                break
        
        false_block = {
            "id": false_block_id,
            "statements": false_typed_statements,
            "terminator": "revert" if false_has_revert else None,
            "branch_type": "false",
            "accesses": {
                "reads": list(false_reads),
                "writes": list(false_writes)
            }
        }
        
        # Check if we have a revert in either branch - this is key for merging blocks correctly
        true_has_revert = contains_revert
        true_has_content = len(true_typed_statements) > 0
        false_has_content = len(false_typed_statements) > 0
        
        # Connect to next block if it exists
        next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
        
        # Set terminators for each block
        # If branch has revert, set it properly as a real terminator, not a goto
        if true_has_revert:
            true_block["terminator"] = "revert"
        elif next_block_id and true_has_content:
            true_block["terminator"] = f"goto {next_block_id}"
            
        if false_has_revert:
            false_block["terminator"] = "revert"
        elif next_block_id and false_has_content:
            false_block["terminator"] = f"goto {next_block_id}"
        
        # Add conditional block to output
        new_blocks.append(conditional_block)
        
        # Determine where branches should point
        if true_has_content or true_has_revert:
            # True branch has content or is a revert, use it
            if false_has_content or false_has_revert:
                # Both branches have content, point to them
                conditional_block["terminator"] = f"if {condition} then goto {true_block_id} else goto {false_block_id}"
                new_blocks.append(true_block)
                new_blocks.append(false_block)
            else:
                # Only true branch has content
                if next_block_id:
                    conditional_block["terminator"] = f"if {condition} then goto {true_block_id} else goto {next_block_id}"
                else:
                    # No next block, use return as terminator for false branch
                    conditional_block["terminator"] = f"if {condition} then goto {true_block_id} else return"
                new_blocks.append(true_block)  # Only add true block
            
        elif false_has_content or false_has_revert:
            # Only false branch has content
            if next_block_id:
                conditional_block["terminator"] = f"if {condition} then goto {next_block_id} else goto {false_block_id}"
            else:
                # No next block, use return as terminator for true branch
                conditional_block["terminator"] = f"if {condition} then return else goto {false_block_id}"
            new_blocks.append(false_block)  # Only add false block
            
        else:
            # Neither branch has content, skip both
            if next_block_id:
                conditional_block["terminator"] = f"goto {next_block_id}"
            else:
                # No next block, just return
                conditional_block["terminator"] = "return"
        
        return new_blocks, block_counter
    
    def _handle_for_loop(self, block, block_idx, block_counter, basic_blocks):
        """
        Process a for loop block into initialization, header, body, increment, and exit blocks.
        
        Args:
            block (dict): The basic block containing a for loop
            block_idx (int): Index of this block in the original list
            block_counter (int): Counter for generating new block IDs
            basic_blocks (list): Complete list of basic blocks
            
        Returns:
            tuple: (new_blocks, updated_block_counter)
        """
        new_blocks = []
        
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
        
        # Create initialization block
        init_block = self._create_init_block(block["id"], pre_loop_statements, initialization)
        
        # Create header block
        header_block_id = f"Block{block_counter}"
        block_counter += 1
        header_block = self._create_header_block(header_block_id, condition)
        
        # Create body block
        body_block_id = f"Block{block_counter}"
        block_counter += 1
        body_block = self._create_body_block(body_block_id, loop_node)
        
        # Create increment block
        increment_block_id = f"Block{block_counter}"
        block_counter += 1
        increment_block = self._create_increment_block(increment_block_id, increment)
        
        # Create exit block
        exit_block_id = f"Block{block_counter}"
        block_counter += 1
        exit_block = self._create_exit_block(exit_block_id)
        
        # Set up the loop control flow connections
        init_block["terminator"] = f"goto {header_block_id}"
        header_block["terminator"] = f"if {condition} then goto {body_block_id} else goto {exit_block_id}"
        body_block["terminator"] = f"goto {increment_block_id}"
        increment_block["terminator"] = f"goto {header_block_id}"  # Loop back edge
        
        # Connect to next block if it exists
        next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
        if next_block_id:
            exit_block["terminator"] = f"goto {next_block_id}"
        
        # Add all blocks to result
        new_blocks.append(init_block)
        new_blocks.append(header_block)
        new_blocks.append(body_block)
        new_blocks.append(increment_block)
        new_blocks.append(exit_block)
        
        return new_blocks, block_counter
    
    def _handle_while_loop(self, block, block_idx, block_counter, basic_blocks):
        """
        Process a while loop block into pre-loop, header, body, and exit blocks.
        
        Args:
            block (dict): The basic block containing a while loop
            block_idx (int): Index of this block in the original list
            block_counter (int): Counter for generating new block IDs
            basic_blocks (list): Complete list of basic blocks
            
        Returns:
            tuple: (new_blocks, updated_block_counter)
        """
        new_blocks = []
        
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
        
        # Create pre-loop block
        pre_block = {
            "id": block["id"],
            "statements": pre_loop_statements,
            "terminator": None
        }
        
        # Create header block
        header_block_id = f"Block{block_counter}"
        block_counter += 1
        header_block = self._create_header_block(header_block_id, condition)
        
        # Create body block
        body_block_id = f"Block{block_counter}"
        block_counter += 1
        body_block = self._create_body_block(body_block_id, loop_node)
        
        # Create exit block
        exit_block_id = f"Block{block_counter}"
        block_counter += 1
        exit_block = self._create_exit_block(exit_block_id)
        
        # Set up the loop control flow connections
        pre_block["terminator"] = f"goto {header_block_id}"
        header_block["terminator"] = f"if {condition} then goto {body_block_id} else goto {exit_block_id}"
        body_block["terminator"] = f"goto {header_block_id}"  # Loop back edge
        
        # Connect to next block if it exists
        next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
        if next_block_id:
            exit_block["terminator"] = f"goto {next_block_id}"
        
        # Add all blocks to result
        new_blocks.append(pre_block)
        new_blocks.append(header_block)
        new_blocks.append(body_block)
        new_blocks.append(exit_block)
        
        return new_blocks, block_counter
    
    def _get_typed_statements(self, statements):
        """
        Convert raw statements to typed statements.
        
        Args:
            statements (list): List of raw statement nodes
            
        Returns:
            list: List of typed statement dictionaries
        """
        return [{"type": get_statement_type(stmt), "node": stmt} for stmt in statements]
    
    def _create_init_block(self, block_id, pre_statements, initialization):
        """
        Create an initialization block for for-loops.
        
        Args:
            block_id (str): Block ID to use
            pre_statements (list): Statements before the loop
            initialization (dict): Initialization expression node
            
        Returns:
            dict: Initialization block dictionary
        """
        init_statements = pre_statements
        if initialization:
            init_statements = pre_statements + [{
                "type": get_statement_type(initialization), 
                "node": initialization
            }]
            
        return {
            "id": block_id,
            "statements": init_statements,
            "terminator": None,
            "is_loop_init": True
        }
    
    def _create_header_block(self, block_id, condition):
        """
        Create a loop header block with condition.
        
        Args:
            block_id (str): Block ID to use
            condition (dict): Condition expression node
            
        Returns:
            dict: Header block dictionary
        """
        statements = []
        if condition:
            statements = [{
                "type": "Expression", 
                "node": {"nodeType": "Expression", "expression": condition}
            }]
            
        return {
            "id": block_id,
            "statements": statements,
            "terminator": None,
            "is_loop_header": True
        }
    
    def _create_body_block(self, block_id, loop_node):
        """
        Create a loop body block.
        
        Args:
            block_id (str): Block ID to use
            loop_node (dict): Loop node containing the body
            
        Returns:
            dict: Body block dictionary
        """
        body = loop_node.get("body", {})
        body_statements = body.get("statements", []) if body else []
        body_typed_statements = self._get_typed_statements(body_statements)
        
        # Track reads/writes for the body statements
        body_reads, body_writes = self._extract_loop_body_accesses(body_statements)
        
        return {
            "id": block_id,
            "statements": body_typed_statements,
            "terminator": None,
            "is_loop_body": True,
            "accesses": {
                "reads": list(body_reads),
                "writes": list(body_writes)
            }
        }
    
    def _create_increment_block(self, block_id, increment):
        """
        Create a loop increment block.
        
        Args:
            block_id (str): Block ID to use
            increment (dict): Increment expression node
            
        Returns:
            dict: Increment block dictionary
        """
        statements = []
        if increment:
            statements = [{
                "type": get_statement_type(increment), 
                "node": increment
            }]
            
        return {
            "id": block_id,
            "statements": statements,
            "terminator": None,
            "is_loop_increment": True
        }
    
    def _create_exit_block(self, block_id):
        """
        Create a loop exit block.
        
        Args:
            block_id (str): Block ID to use
            
        Returns:
            dict: Exit block dictionary
        """
        return {
            "id": block_id,
            "statements": [],
            "terminator": None,
            "is_loop_exit": True
        }
    
    def _extract_loop_body_accesses(self, body_statements):
        """
        Extract variable reads and writes from loop body statements.
        
        Args:
            body_statements (list): List of statement nodes
            
        Returns:
            tuple: (reads, writes) sets of variable names
        """
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
        
        return body_reads, body_writes


# For backward compatibility
def finalize_terminators(basic_blocks):
    """
    Ensure all blocks have correct terminators for complete control flow.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of basic block dictionaries with updated terminators
    """
    return ControlFlowRefiner.finalize_terminators(basic_blocks)


def refine_blocks_with_control_flow(basic_blocks):
    """
    Refine basic blocks to handle control flow splits from IfStatements and Loops.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of refined basic block dictionaries with control flow
    """
    return ControlFlowRefiner.refine_blocks_with_control_flow(basic_blocks)