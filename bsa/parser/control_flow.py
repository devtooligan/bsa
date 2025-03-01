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
        true_typed_statements = self._get_typed_statements(true_statements)
        
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
        false_typed_statements = self._get_typed_statements(false_statements)
        
        false_block = {
            "id": false_block_id,
            "statements": false_typed_statements,
            "terminator": None,
            "branch_type": "false"
        }
        
        # Update the conditional block's terminator with goto information
        conditional_block["terminator"] = f"if {condition} then goto {true_block_id} else goto {false_block_id}"
        
        # Connect branches to next block if it exists
        next_block_id = basic_blocks[block_idx + 1]["id"] if block_idx + 1 < len(basic_blocks) else None
        if next_block_id:
            if not true_block["terminator"]:
                true_block["terminator"] = f"goto {next_block_id}"
            if not false_block["terminator"]:
                false_block["terminator"] = f"goto {next_block_id}"
        
        # Add blocks to result
        new_blocks.append(conditional_block)
        new_blocks.append(true_block)
        new_blocks.append(false_block)
        
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