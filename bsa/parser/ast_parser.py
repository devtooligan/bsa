"""
AST parser for BSA.
"""

import os
import json
import glob

from bsa.parser.nodes import ASTNode
from bsa.parser.source_mapper import offset_to_line_col
from bsa.utils.forge import (
    clean_project, 
    build_project_ast, 
    find_source_files, 
    find_ast_files, 
    load_ast_file
)

class ASTParser:
    """Parser for Solidity AST files."""
    
    def __init__(self, project_path):
        """
        Initialize the AST parser.
        
        Args:
            project_path (str): Path to the project directory
        """
        self.project_path = project_path
        self.ast_data = None
        self.source_files = {}
        self.ast_files = []
        self.source_text = ""
    
    def prepare(self):
        """
        Prepare the project by cleaning and building AST.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(self.project_path):
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")
        
        # Clean project
        if not clean_project(self.project_path):
            return False
        
        # Build project AST
        if not build_project_ast(self.project_path):
            return False
        
        # Find source and AST files
        self.source_files = find_source_files(self.project_path)
        self.ast_files = find_ast_files(self.project_path, list(self.source_files.keys()))
        
        return len(self.ast_files) > 0
    
    def parse(self):
        """
        Parse AST files and extract contract data.
        
        Returns:
            list: List of contract data dictionaries
        """
        output = []
        
        # Ensure preparation has been done
        if not self.ast_files:
            if not self.prepare():
                return output
        
        # Process each AST file
        for ast_file in self.ast_files:
            # Extract contract name from the AST file path
            file_dir = os.path.dirname(ast_file)
            contract_file = os.path.basename(file_dir)
            contract_name = contract_file[:-4] if contract_file.endswith(".sol") else contract_file
            
            # Get the corresponding source file path
            src_file_path = self.source_files.get(contract_name)
            
            # Load the source file
            self.source_text = ""
            if src_file_path and os.path.exists(src_file_path):
                with open(src_file_path, "r") as src_file:
                    self.source_text = src_file.read()
            
            # Load the AST file
            ast_data = load_ast_file(ast_file)
            ast = ast_data.get("ast", {})
            
            # Process the AST
            contract_data = self._process_ast(ast)
            
            if contract_data:
                output.extend(contract_data)
        
        return output
    
    def _process_ast(self, ast):
        """
        Process an AST and extract contract data.
        
        Args:
            ast (dict): The AST data
            
        Returns:
            list: List of contract data dictionaries
        """
        output = []
        
        # Get nodes list from the AST
        nodes = ast.get("nodes", [])
        
        # Parse each node in the nodes list into an ASTNode
        ast_nodes = []
        for node in nodes:
            node_instance = ASTNode(node)
            ast_nodes.append(node_instance)
        
        # Find pragma directive
        pragma = ""
        for node in ast_nodes:
            if node.node_type == "PragmaDirective":
                literals = node.get("literals", [])
                if literals:
                    pragma = " ".join(literals)
        
        # Process each contract definition
        for node in ast_nodes:
            if node.node_type == "ContractDefinition":
                contract_data = self._process_contract_definition(node, pragma)
                if contract_data:
                    output.append(contract_data)
        
        return output
    
    def extract_function_body(self, node):
        """
        Extract the raw statements list from a function definition.
        
        Args:
            node (ASTNode or dict): Function definition node
            
        Returns:
            list: Raw statements list from the function body
        """
        # Get the body node (a Block node)
        body = node.get("body", {}) if isinstance(node, ASTNode) else node.get("body", {})
        
        # Extract statements list, defaulting to empty list if missing
        statements = body.get("statements", [])
        
        return statements
        
    def classify_statements(self, statements):
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
        
    def split_into_basic_blocks(self, statements_typed):
        """
        Split typed statements into basic blocks based on control flow, function calls, and state writes.
        
        Args:
            statements_typed (list): List of typed statement dictionaries
            
        Returns:
            list: List of basic block dictionaries
        """
        # Control flow statement types that terminate a basic block
        block_terminators = ["IfStatement", "ForLoop", "WhileLoop", "Return"]
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
        
    def _get_statement_type(self, stmt):
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
    
    def refine_blocks_with_control_flow(self, basic_blocks):
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
                true_typed_statements = [{"type": self._get_statement_type(stmt), "node": stmt} for stmt in true_statements]
                
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
                false_typed_statements = [{"type": self._get_statement_type(stmt), "node": stmt} for stmt in false_statements]
                
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
                        "type": self._get_statement_type(initialization), 
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
                body_typed_statements = [{"type": self._get_statement_type(stmt), "node": stmt} for stmt in body_statements]
                
                body_block = {
                    "id": body_block_id,
                    "statements": body_typed_statements,
                    "terminator": None,
                    "is_loop_body": True
                }
                
                # Create loop increment block
                increment_block_id = f"Block{block_counter}"
                block_counter += 1
                
                increment_block = {
                    "id": increment_block_id,
                    "statements": [{
                        "type": self._get_statement_type(increment), 
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
                body_typed_statements = [{"type": self._get_statement_type(stmt), "node": stmt} for stmt in body_statements]
                
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
        
    def track_variable_accesses(self, basic_blocks):
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
                            # For struct fields, add the base variable
                            base_expr = left_hand_side.get("expression", {})
                            if base_expr.get("nodeType") == "Identifier":
                                writes.add(base_expr.get("name", ""))
                        elif left_hand_side.get("nodeType") == "IndexAccess":
                            # For arrays/mappings, add the base variable
                            base_expr = left_hand_side.get("baseExpression", {})
                            if base_expr.get("nodeType") == "Identifier":
                                writes.add(base_expr.get("name", ""))
                        
                        # Handle reads on the right side
                        right_hand_side = expression.get("rightHandSide", {})
                        self._extract_reads(right_hand_side, reads)
                
                elif stmt_type == "FunctionCall":
                    if node["nodeType"] == "ExpressionStatement":
                        expression = node.get("expression", {})
                        
                        # Extract function arguments as reads
                        if expression.get("nodeType") == "FunctionCall":
                            for arg in expression.get("arguments", []):
                                self._extract_reads(arg, reads)
                
                elif stmt_type == "IfStatement":
                    # Extract condition variables as reads
                    condition = node.get("condition", {})
                    self._extract_reads(condition, reads)
                
                elif stmt_type == "Return":
                    # Extract expression variables as reads
                    expression = node.get("expression", {})
                    if expression:
                        self._extract_reads(expression, reads)
                
                elif stmt_type == "VariableDeclaration":
                    # Handle variable declarations
                    declarations = node.get("declarations", [])
                    for decl in declarations:
                        if decl and decl.get("nodeType") == "VariableDeclaration":
                            writes.add(decl.get("name", ""))
                    
                    # Handle initialization value as reads
                    init_value = node.get("initialValue", {})
                    if init_value:
                        self._extract_reads(init_value, reads)
                
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
                                self._extract_reads(init_value, reads)
                        # Check if it's an assignment
                        elif init.get("nodeType") == "ExpressionStatement":
                            expr = init.get("expression", {})
                            if expr.get("nodeType") == "Assignment":
                                left = expr.get("leftHandSide", {})
                                if left.get("nodeType") == "Identifier":
                                    writes.add(left.get("name", ""))
                                
                                right = expr.get("rightHandSide", {})
                                self._extract_reads(right, reads)
                    
                    # Condition (e.g., i < 10)
                    condition = node.get("condition", {})
                    if condition:
                        self._extract_reads(condition, reads)
                    
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
                                    self._extract_reads(expr, reads)
                                elif expr.get("nodeType") == "Assignment":
                                    left = expr.get("leftHandSide", {})
                                    if left.get("nodeType") == "Identifier":
                                        writes.add(left.get("name", ""))
                                    
                                    right = expr.get("rightHandSide", {})
                                    self._extract_reads(right, reads)
                
                elif stmt_type == "WhileLoop":
                    # Handle while loop components
                    
                    # Condition (e.g., i < 10)
                    condition = node.get("condition", {})
                    if condition:
                        self._extract_reads(condition, reads)
                    
                    # The body is handled separately as part of the body block
            
            # Special handling for loop header blocks
            if block.get("is_loop_header", False):
                # If this is a loop header block and the statement is an expression for the condition
                if block["statements"] and block["statements"][0]["type"] == "Expression":
                    condition = block["statements"][0]["node"].get("expression", {})
                    self._extract_reads(condition, reads)
            
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
                            self._extract_reads(right, reads)
            
            # Remove empty strings
            reads.discard("")
            writes.discard("")
            
            # Add accesses to the block
            block["accesses"] = {
                "reads": list(reads),
                "writes": list(writes)
            }
        
        return basic_blocks
    
    def _extract_reads(self, node, reads_set):
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
            self._extract_reads(node.get("leftExpression", {}), reads_set)
            self._extract_reads(node.get("rightExpression", {}), reads_set)
        
        elif node_type == "MemberAccess":
            # For struct fields, consider the base variable as read
            base_expr = node.get("expression", {})
            if base_expr.get("nodeType") == "Identifier":
                reads_set.add(base_expr.get("name", ""))
        
        elif node_type == "IndexAccess":
            # For arrays/mappings, consider the base variable as read
            base_expr = node.get("baseExpression", {})
            if base_expr.get("nodeType") == "Identifier":
                reads_set.add(base_expr.get("name", ""))
            
            # Also consider the index expression variables as reads
            index_expr = node.get("indexExpression", {})
            self._extract_reads(index_expr, reads_set)
        
        elif node_type == "FunctionCall":
            # Consider function arguments as reads
            for arg in node.get("arguments", []):
                self._extract_reads(arg, reads_set)
            
            # For method calls, consider the base object as read
            expr = node.get("expression", {})
            if expr.get("nodeType") == "MemberAccess":
                base = expr.get("expression", {})
                self._extract_reads(base, reads_set)
                
    def assign_ssa_versions(self, basic_blocks):
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
        
        # Second pass: assign versions to each block
        for block in basic_blocks:
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
            
            # Create SSA statements
            block["ssa_statements"] = []
            
            for statement in block["statements"]:
                stmt_type = statement["type"]
                node = statement["node"]
                
                if stmt_type == "Assignment":
                    if node["nodeType"] == "ExpressionStatement":
                        expression = node.get("expression", {})
                        left_hand_side = expression.get("leftHandSide", {})
                        right_hand_side = expression.get("rightHandSide", {})
                        
                        # Get variable name and its SSA version
                        if left_hand_side.get("nodeType") == "Identifier":
                            var_name = left_hand_side.get("name", "")
                            var_version = writes_dict.get(var_name, 0)
                            
                            # Create SSA assignment statement
                            ssa_stmt = f"{var_name}_{var_version} = "
                            
                            # Extract reads from right-hand side and append versioned variables
                            rhs_reads = set()
                            self._extract_reads(right_hand_side, rhs_reads)
                            
                            # Simple representation of right side - just append all versioned reads
                            for read_var in rhs_reads:
                                read_version = reads_dict.get(read_var, 0)
                                ssa_stmt += f"{read_var}_{read_version} "
                            
                            # Add the SSA statement to the block
                            block["ssa_statements"].append(ssa_stmt)
                
                elif stmt_type == "IfStatement":
                    condition = node.get("condition", {})
                    
                    # Extract condition variables
                    cond_reads = set()
                    self._extract_reads(condition, cond_reads)
                    
                    # Get variable explicitly from condition for if statement
                    var_name = ""
                    if condition.get("nodeType") == "BinaryOperation":
                        left = condition.get("leftExpression", {})
                        if left.get("nodeType") == "Identifier":
                            var_name = left.get("name", "")
                    
                    # Create SSA condition statement
                    ssa_stmt = "if ("
                    if var_name and var_name in reads_dict:
                        var_version = reads_dict[var_name]
                        ssa_stmt += f"{var_name}_{var_version}"
                    elif cond_reads:
                        for read_var in cond_reads:
                            read_version = reads_dict.get(read_var, 0)
                            ssa_stmt += f"{read_var}_{read_version} "
                    ssa_stmt += ")"
                    
                    # Add the SSA statement to the block
                    block["ssa_statements"].append(ssa_stmt)
                
                elif stmt_type == "FunctionCall":
                    if node["nodeType"] == "ExpressionStatement":
                        expression = node.get("expression", {})
                        
                        # Create SSA function call statement
                        ssa_stmt = "call("
                        
                        # Extract argument variables
                        arg_reads = set()
                        for arg in expression.get("arguments", []):
                            self._extract_reads(arg, arg_reads)
                        
                        # Append versioned argument variables
                        for read_var in arg_reads:
                            read_version = reads_dict.get(read_var, 0)
                            ssa_stmt += f"{read_var}_{read_version} "
                        ssa_stmt += ")"
                        
                        # Add the SSA statement to the block
                        block["ssa_statements"].append(ssa_stmt)
                
                elif stmt_type == "Return":
                    expression = node.get("expression", {})
                    
                    # Extract return variables
                    ret_reads = set()
                    self._extract_reads(expression, ret_reads)
                    
                    # Create SSA return statement
                    ssa_stmt = "return "
                    for read_var in ret_reads:
                        read_version = reads_dict.get(read_var, 0)
                        ssa_stmt += f"{read_var}_{read_version} "
                    
                    # Add the SSA statement to the block
                    block["ssa_statements"].append(ssa_stmt)
        
        return basic_blocks
        
    def insert_phi_functions(self, basic_blocks):
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
    
    def finalize_terminators(self, basic_blocks):
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
                
            # For all other blocks, determine if they should goto next block or return
            if idx < len(basic_blocks) - 1:
                # Not the last block, so add goto next block
                next_block = basic_blocks[idx + 1]
                block["terminator"] = f"goto {next_block['id']}"
            else:
                # Last block in function, should return
                block["terminator"] = "return"
        
        return basic_blocks
        
    def integrate_ssa_output(self, basic_blocks):
        """
        Create a clean SSA representation from the basic blocks.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with SSA information
            
        Returns:
            list: List of simplified SSA block dictionaries with ID, statements, and terminators
        """
        if not basic_blocks:
            return []
            
        ssa_blocks = []
        
        for block in basic_blocks:
            # Extract only the essential SSA information
            ssa_block = {
                "id": block["id"],
                "ssa_statements": block.get("ssa_statements", []),
                "terminator": block.get("terminator", None)
            }
            
            # Add block to the list
            ssa_blocks.append(ssa_block)
            
        return ssa_blocks
    
    def inline_internal_calls(self, basic_blocks, function_map, entrypoints_data=None):
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
        
        # Process each block for function calls
        for block in basic_blocks:
            # Skip blocks with no SSA statements
            if "ssa_statements" not in block:
                continue
                
            # Get current variable versions from this block
            for var, version in block.get("ssa_versions", {}).get("writes", {}).items():
                if var not in version_counter:
                    version_counter[var] = 0
                version_counter[var] = max(version_counter[var], version)
            
            # Find internal calls in the block
            modified_statements = []
            added_reads = set()
            added_writes = set()
            
            for stmt in block["ssa_statements"]:
                # Check if this is an internal function call
                if "call[internal]" in stmt:
                    # Extract function name and arguments
                    func_name = stmt.split("call[internal](")[1].split(",")[0].strip(") ")
                    
                    # Look up the function's SSA data
                    if func_name in function_ssa:
                        target_ssa = function_ssa[func_name]
                        
                        # First add the original call for reference
                        modified_statements.append(stmt)
                        
                        # Collect all inlined statements from all target blocks
                        all_inlined_statements = []
                        
                        # Inline each block from the target function
                        for target_block in target_ssa:
                            target_statements = target_block.get("ssa_statements", [])
                            
                            # Process each statement in the target function
                            for target_stmt in target_statements:
                                # Skip phi functions (they don't transfer well across function boundaries)
                                if "= phi(" in target_stmt:
                                    continue
                                    
                                # Update variable versions to avoid conflicts
                                inlined_stmt = target_stmt
                                
                                # Find variables in the statement and update their versions
                                for var in version_counter:
                                    var_pattern = f"{var}_"
                                    if var_pattern in inlined_stmt:
                                        # Extract all versions of this variable from the statement
                                        # This requires a more sophisticated regex approach in reality
                                        # For simplicity, we'll do basic replacements here
                                        for i in range(10):  # Assuming versions 0-9 for simplicity
                                            old_var = f"{var}_{i}"
                                            if old_var in inlined_stmt:
                                                # Increment the version counter
                                                version_counter[var] += 1
                                                new_var = f"{var}_{version_counter[var]}"
                                                inlined_stmt = inlined_stmt.replace(old_var, new_var)
                                                
                                                # Track variables being read/written
                                                if " = " in inlined_stmt and inlined_stmt.startswith(new_var):
                                                    added_writes.add(var)
                                                else:
                                                    added_reads.add(var)
                                
                                # Add the inlined statement to our collected inlined statements
                                all_inlined_statements.append(inlined_stmt)
                                
                                # Directly update accesses based on this statement
                                # We track them in added_reads/writes for bulk update,
                                # but we also want to immediately update the block's accesses
                                if "writes" not in block["accesses"]:
                                    block["accesses"]["writes"] = []
                                    
                                # Extract variable from the statement
                                if " = " in inlined_stmt:
                                    var_name = None
                                    if "_" in inlined_stmt.split(" = ")[0]:
                                        var_name = inlined_stmt.split(" = ")[0].split("_")[0]
                                    if var_name and var_name not in block["accesses"]["writes"]:
                                        block["accesses"]["writes"].append(var_name)
                        
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
                
                # Update with added reads and writes
                reads = set(block["accesses"]["reads"])
                writes = set(block["accesses"]["writes"])
                reads.update(added_reads)
                writes.update(added_writes)
                block["accesses"]["reads"] = list(reads)
                block["accesses"]["writes"] = list(writes)
        
        return basic_blocks
    
    def analyze_loop_calls(self, basic_blocks):
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
    
    def classify_and_add_calls(self, basic_blocks, function_map):
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
            # Find function call statements
            function_calls = []
            for i, stmt in enumerate(block.get("statements", [])):
                if stmt.get("type") == "FunctionCall":
                    function_calls.append(i)
            
            # Skip if there are no function calls
            if not function_calls:
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
                if stmt.startswith("call("):
                    call_stmt_indices.append(i)
            
            # Process each function call
            for call_idx in range(min(len(function_calls), len(call_stmt_indices))):
                stmt_idx = call_stmt_indices[call_idx]
                stmt_node_idx = function_calls[call_idx]
                
                # Get the function call node
                call_node = block["statements"][stmt_node_idx]["node"]
                
                # Get the expression containing the function call
                expr = call_node.get("expression", {})
                if expr.get("nodeType") == "FunctionCall":
                    func_expr = expr.get("expression", {})
                    
                    # Determine the type of function call
                    call_type = "unknown"
                    call_name = "unknown"
                    
                    # Function name and target analysis
                    if func_expr.get("nodeType") == "Identifier":
                        # Direct function call: foo()
                        call_name = func_expr.get("name", "unknown")
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
                    if call_stmt.startswith("call("):
                        # Create enhanced call statement based on type and name
                        ret_counter += 1
                        enhanced_stmt = f"ret_{ret_counter} = call[{call_type}]({call_name}"
                        
                        # Extract arguments
                        if "(" in call_stmt:
                            args_part = call_stmt.split("(", 1)[1].strip(")")
                            if args_part.strip():  # If there are arguments
                                enhanced_stmt += f", {args_part}"
                        
                        enhanced_stmt += ")"
                        
                        # Replace the statement
                        modified_statements[stmt_idx] = enhanced_stmt
            
            # Update the block with modified statements
            block["ssa_statements"] = modified_statements
        
        return basic_blocks
        
    def _process_contract_definition(self, node, pragma):
        """
        Process a contract definition node to extract contract data.
        
        Args:
            node (ASTNode): The contract definition AST node
            pragma (str): The pragma directive string
            
        Returns:
            dict: Dictionary with contract data
        """
        # Extract contract name and location
        contract_name = node.get("name", "Unknown")
        
        # Get the contract's source location (if available)
        src = node.get("src", "")
        line, col = 0, 0
        if src:
            offsets = src.split(":", 1)[0]
            line, col = offset_to_line_col(int(offsets), self.source_text)
        
        # Initialize outputs
        state_vars = []
        functions = {}
        events = []
        
        # Process contract body nodes to extract information
        nodes = node.get("nodes", [])
        function_map = {}  # Maps function names to their AST nodes (for call detection)
        
        for subnode in nodes:
            node_type = subnode.get("nodeType", "")
            
            if node_type == "VariableDeclaration" and subnode.get("stateVariable", False):
                # Extract state variable information
                var_name = subnode.get("name", "")
                var_type = ""
                
                # Get variable type
                type_node = subnode.get("typeName", {})
                if type_node:
                    var_type = type_node.get("name", "unknown")
                
                # Get variable location
                var_src = subnode.get("src", "")
                var_line, var_col = 0, 0
                if var_src:
                    offsets = var_src.split(":", 1)[0]
                    var_line, var_col = offset_to_line_col(int(offsets), self.source_text)
                
                state_vars.append({
                    "name": var_name,
                    "type": var_type,
                    "location": [var_line, var_col]
                })
            
            elif node_type == "FunctionDefinition":
                # Extract function information
                func_name = subnode.get("name", "")
                visibility = subnode.get("visibility", "internal")
                
                # Get function location
                func_src = subnode.get("src", "")
                func_line, func_col = 0, 0
                if func_src:
                    offsets = func_src.split(":", 1)[0]
                    func_line, func_col = offset_to_line_col(int(offsets), self.source_text)
                
                functions[func_name] = {
                    "visibility": visibility,
                    "location": [func_line, func_col]
                }
                
                # Add to function map for call detection
                function_map[func_name] = subnode
            
            elif node_type == "EventDefinition":
                # Extract event information
                event_name = subnode.get("name", "")
                
                # Get event location
                event_src = subnode.get("src", "")
                event_line, event_col = 0, 0
                if event_src:
                    offsets = event_src.split(":", 1)[0]
                    event_line, event_col = offset_to_line_col(int(offsets), self.source_text)
                
                events.append({
                    "name": event_name,
                    "location": [event_line, event_col]
                })
        
        # First, process all functions (both internal and external) to build complete SSA data
        all_funcs_ssa = {}
        internal_functions = []
        entrypoints = []
        
        # Process all functions to build SSA data
        for func_name, func_info in functions.items():
            function_node = function_map.get(func_name)
            if not function_node:
                continue
                
            # Extract function calls from body
            calls = []
            calls_seen = set()  # To avoid duplicates
            
            body_raw = self.extract_function_body(function_node)
            statements_typed = self.classify_statements(body_raw)
            basic_blocks = self.split_into_basic_blocks(statements_typed)
            refined_blocks = self.refine_blocks_with_control_flow(basic_blocks)
            
            # Track variable accesses across blocks
            blocks_with_accesses = self.track_variable_accesses(refined_blocks)
            
            # Assign SSA versions to variable accesses
            blocks_with_ssa = self.assign_ssa_versions(blocks_with_accesses)
            
            # Classify and add function calls
            blocks_with_calls = self.classify_and_add_calls(blocks_with_ssa, function_map)
            
            # Analyze loops with function calls for enhanced phi generation
            blocks_with_loop_calls = self.analyze_loop_calls(blocks_with_calls)
            
            # Insert phi functions at merge points
            blocks_with_phi = self.insert_phi_functions(blocks_with_loop_calls)
            
            # Get the base SSA data before inlining (we'll finalize later)
            base_ssa_output = self.integrate_ssa_output(blocks_with_phi)
            
            # Create a function data record
            func_data = {
                "name": func_name,
                "location": func_info.get("location", [0, 0]),
                "visibility": func_info.get("visibility", ""),
                "calls": [],  # We'll fill this later
                "body_raw": body_raw,
                "basic_blocks": blocks_with_phi,
                "ssa": base_ssa_output
            }
            
            # Store in appropriate list based on visibility
            visibility = func_info.get("visibility", "")
            if visibility in ["external", "public"]:
                entrypoints.append(func_data)
            else:
                internal_functions.append(func_data)
            
            # Store for reference during inlining
            all_funcs_ssa[func_name] = func_data
        
        # After processing all functions, perform inlining on each function
        for func_data in entrypoints + internal_functions:
            # Inline internal function calls
            blocks_with_inlined_calls = self.inline_internal_calls(
                func_data["basic_blocks"], 
                function_map, 
                entrypoints + internal_functions
            )
            
            # Finalize block terminators after inlining
            blocks_with_terminators = self.finalize_terminators(blocks_with_inlined_calls)
            
            # Generate final SSA output with inlined calls
            ssa_output = self.integrate_ssa_output(blocks_with_terminators)
            
            # Update the function data
            func_data["basic_blocks"] = blocks_with_terminators
            func_data["ssa"] = ssa_output
            
            # Extract function calls information for reporting
            calls = []
            calls_seen = set()
            for block in func_data["basic_blocks"]:
                for stmt in block.get("ssa_statements", []):
                    if "call[" in stmt:
                        if "call[internal]" in stmt:
                            # Extract internal call name
                            call_name = stmt.split("call[internal](")[1].split(",")[0].strip(") ")
                            if call_name not in calls_seen:
                                calls_seen.add(call_name)
                                calls.append({
                                    "name": call_name,
                                    "in_contract": True,
                                    "is_external": False,
                                    "call_type": "internal",
                                    "location": [0, 0]  # We'd need more context to get exact location
                                })
                        elif "call[external]" in stmt:
                            # Extract external call name
                            call_name = stmt.split("call[external](")[1].split(",")[0].strip(") ")
                            if call_name not in calls_seen:
                                calls_seen.add(call_name)
                                calls.append({
                                    "name": call_name,
                                    "in_contract": False,
                                    "is_external": True,
                                    "call_type": "external",
                                    "location": [0, 0]  # We'd need more context to get exact location
                                })
            
            # Update the calls list
            func_data["calls"] = calls
                
        # Define call extraction helper function once
        def extract_calls(node, calls, calls_seen):
            if not node:
                return
                
            node_type = node.get("nodeType", "")
            
            if node_type == "FunctionCall":
                expr = node.get("expression", {})
                expr_type = expr.get("nodeType", "")
                
                # Direct function call (foo())
                if expr_type == "Identifier":
                    call_name = expr.get("name", "unknown")
                    if call_name not in calls_seen:
                        calls_seen.add(call_name)
                        src = expr.get("src", "")
                        line, col = 0, 0
                        if src:
                            offsets = src.split(":", 1)[0]
                            line, col = offset_to_line_col(int(offsets), self.source_text)
                        
                        # Determine if internal or external
                        is_internal = call_name in function_map
                        
                        calls.append({
                            "name": call_name,
                            "in_contract": is_internal,
                            "is_external": not is_internal,
                            "call_type": "internal" if is_internal else "external",
                            "location": [line, col]
                        })
                
                # Member call (obj.foo())
                elif expr_type == "MemberAccess":
                    member_name = expr.get("memberName", "unknown")
                    base_expr = expr.get("expression", {})
                    
                    # Skip standard library calls
                    if member_name in ["call", "delegatecall", "staticcall", "transfer", "send"]:
                        return
                    
                    # Determine call type
                    call_type = "external"  # Default to external
                    
                    # Check for contract cast or interface calls
                    if base_expr.get("nodeType") == "FunctionCall":
                        call_type = "external"
                    elif base_expr.get("nodeType") == "Identifier":
                        base_name = base_expr.get("name", "")
                        # Check type information if available
                        type_descriptions = base_expr.get("typeDescriptions", {})
                        type_string = type_descriptions.get("typeString", "")
                        
                        # If type string indicates contract or interface, it's external
                        if "contract" in type_string.lower() or "interface" in type_string.lower():
                            call_type = "external"
                        elif base_name in function_map:
                            call_type = "internal"
                    
                    if member_name not in calls_seen:
                        calls_seen.add(member_name)
                        src = expr.get("src", "")
                        line, col = 0, 0
                        if src:
                            offsets = src.split(":", 1)[0]
                            line, col = offset_to_line_col(int(offsets), self.source_text)
                        
                        is_internal = call_type == "internal"
                        
                        calls.append({
                            "name": member_name,
                            "in_contract": is_internal,
                            "is_external": not is_internal,
                            "call_type": call_type,
                            "location": [line, col]
                        })
            
            # Recursively process sub-components
            for key, value in node.items():
                if isinstance(value, dict):
                    extract_calls(value, calls, calls_seen)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            extract_calls(item, calls, calls_seen)
        
        # Extract function calls from the raw AST for better location information
        for entrypoint in entrypoints:
            # Get better location information from AST
            raw_calls = []
            raw_calls_seen = set()
            for statement in entrypoint["body_raw"]:
                extract_calls(statement, raw_calls, raw_calls_seen)
                
            # Combine with existing calls (preserve accurate locations)
            for raw_call in raw_calls:
                # Check if this call is already in the list
                for existing_call in entrypoint["calls"]:
                    if existing_call["name"] == raw_call["name"]:
                        # Update the location
                        existing_call["location"] = raw_call["location"]
                        break
        
        # Construct the contract data dictionary
        contract_data = {
            "contract": {
                "name": contract_name,
                "pragma": pragma,
                "state_vars": state_vars,
                "functions": functions,
                "events": events
            },
            "entrypoints": entrypoints
        }
        
        return contract_data