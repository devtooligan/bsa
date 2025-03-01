"""
Core parser functionality for BSA.
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

from bsa.parser.basic_blocks import (
    classify_statements,
    split_into_basic_blocks
)
from bsa.parser.control_flow import refine_blocks_with_control_flow
from bsa.parser.variable_tracking import track_variable_accesses
from bsa.parser.ssa_conversion import SSAConverter, convert_to_ssa
from bsa.parser.function_calls import (
    classify_and_add_calls,
    inline_internal_calls
)
from bsa.parser.loop_analysis import analyze_loop_calls

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
        
        # Process all contract data to ensure consistency
        for contract_data in output:
            if not contract_data.get("entrypoints"):
                continue
                
            # Process each entrypoint for consistent formatting
            for entrypoint in contract_data["entrypoints"]:
                if entrypoint.get("ssa") and isinstance(entrypoint["ssa"], list):
                    for block in entrypoint["ssa"]:
                        if "ssa_statements" not in block:
                            continue
                            
                        # Format statements consistently
                        for i, stmt in enumerate(block["ssa_statements"]):
                            # Standardize call[internal] argument formatting with commas
                            if "call[internal](" in stmt:
                                # Extract the call parts
                                call_prefix = stmt.split("call[internal](")[0] + "call[internal]("
                                call_parts = stmt.split("call[internal](")[1].strip(")")
                                
                                # Parse function name and arguments properly
                                if "," in call_parts:
                                    # Already has commas, keep as is
                                    pass
                                else:
                                    # Need to add commas between function name and args
                                    parts = call_parts.strip().split()
                                    if len(parts) > 1:
                                        # Format with proper commas between function name and args
                                        function_name = parts[0]
                                        args = parts[1:]
                                        formatted_parts = function_name + ", " + ", ".join(args)
                                        block["ssa_statements"][i] = f"{call_prefix}{formatted_parts})"
        
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
                contract_processor = ContractProcessor(node, pragma, self.source_text)
                contract_data = contract_processor.process()
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
        
    def finalize_terminators(self, basic_blocks):
        """
        Ensure all blocks have correct terminators for complete control flow.
        
        Args:
            basic_blocks (list): List of basic block dictionaries
            
        Returns:
            list: List of basic block dictionaries with updated terminators
        """
        # This used to be implemented here, but is now part of control_flow
        # Moving implementation to control_flow is part of the modularization effort
        # Forwarding to control_flow's implementation
        from bsa.parser.control_flow import finalize_terminators
        return finalize_terminators(basic_blocks)
        
    def integrate_ssa_output(self, basic_blocks):
        """
        Create a clean SSA representation from the basic blocks.
        
        Args:
            basic_blocks (list): List of basic block dictionaries with SSA information
            
        Returns:
            list: List of simplified SSA block dictionaries with ID, statements, terminators, and variable accesses
        """
        # This used to be implemented here, but is now part of ssa_conversion
        # Moving implementation to SSAConverter is part of the modularization effort
        # Forwarding to SSAConverter's implementation
        return SSAConverter.integrate_ssa_output(basic_blocks)


class ContractProcessor:
    """
    Handles processing of Solidity contract definition nodes.
    """
    
    def __init__(self, node, pragma, source_text):
        """
        Initialize the contract processor.
        
        Args:
            node (ASTNode): The contract definition AST node
            pragma (str): The pragma directive string
            source_text (str): The source code text
        """
        self.node = node
        self.pragma = pragma
        self.source_text = source_text
        self.state_vars = []
        self.functions = {}
        self.events = []
        self.function_map = {}
        
    def process(self):
        """
        Process the contract definition to extract data.
        
        Returns:
            dict: Dictionary with contract data
        """
        # Extract basic contract info
        contract_info = self._extract_contract_info()
        
        # Process all nodes in the contract
        self._process_contract_nodes()
        
        # Process all functions to build SSA data
        all_funcs_ssa, internal_functions, entrypoints = self._process_functions()
        
        # Perform function call inlining and refinement
        self._process_function_inlining(entrypoints, internal_functions)
        
        # Extract additional call information
        self._extract_call_information(entrypoints)
        
        # Construct the contract data dictionary
        contract_data = {
            "contract": {
                "name": contract_info["name"],
                "pragma": self.pragma,
                "state_vars": self.state_vars,
                "functions": self.functions,
                "events": self.events
            },
            "entrypoints": entrypoints
        }
        
        return contract_data
        
    def _extract_contract_info(self):
        """
        Extract basic contract information.
        
        Returns:
            dict: Dictionary with contract name and location
        """
        contract_name = self.node.get("name", "Unknown")
        
        # Get the contract's source location (if available)
        src = self.node.get("src", "")
        line, col = 0, 0
        if src:
            offsets = src.split(":", 1)[0]
            line, col = offset_to_line_col(int(offsets), self.source_text)
        
        return {
            "name": contract_name,
            "location": [line, col]
        }
        
    def _process_contract_nodes(self):
        """
        Process all nodes in the contract definition.
        """
        nodes = self.node.get("nodes", [])
        
        for subnode in nodes:
            node_type = subnode.get("nodeType", "")
            
            if node_type == "VariableDeclaration" and subnode.get("stateVariable", False):
                self._process_state_variable(subnode)
            elif node_type == "FunctionDefinition":
                self._process_function_definition(subnode)
            elif node_type == "EventDefinition":
                self._process_event_definition(subnode)
                
    def _process_state_variable(self, node):
        """
        Process a state variable declaration.
        
        Args:
            node (ASTNode): The variable declaration node
        """
        var_name = node.get("name", "")
        var_type = ""
        
        # Get variable type
        type_node = node.get("typeName", {})
        if type_node:
            var_type = type_node.get("name", "unknown")
        
        # Get variable location
        var_src = node.get("src", "")
        var_line, var_col = 0, 0
        if var_src:
            offsets = var_src.split(":", 1)[0]
            var_line, var_col = offset_to_line_col(int(offsets), self.source_text)
        
        self.state_vars.append({
            "name": var_name,
            "type": var_type,
            "location": [var_line, var_col]
        })
        
    def _process_function_definition(self, node):
        """
        Process a function definition.
        
        Args:
            node (ASTNode): The function definition node
        """
        func_name = node.get("name", "")
        visibility = node.get("visibility", "internal")
        
        # Get function location
        func_src = node.get("src", "")
        func_line, func_col = 0, 0
        if func_src:
            offsets = func_src.split(":", 1)[0]
            func_line, func_col = offset_to_line_col(int(offsets), self.source_text)
        
        self.functions[func_name] = {
            "visibility": visibility,
            "location": [func_line, func_col]
        }
        
        # Add to function map for call detection
        self.function_map[func_name] = node
        
    def _process_event_definition(self, node):
        """
        Process an event definition.
        
        Args:
            node (ASTNode): The event definition node
        """
        event_name = node.get("name", "")
        
        # Get event location
        event_src = node.get("src", "")
        event_line, event_col = 0, 0
        if event_src:
            offsets = event_src.split(":", 1)[0]
            event_line, event_col = offset_to_line_col(int(offsets), self.source_text)
        
        self.events.append({
            "name": event_name,
            "location": [event_line, event_col]
        })
        
    def _process_functions(self):
        """
        Process all functions to build SSA data.
        
        Returns:
            tuple: (all_funcs_ssa, internal_functions, entrypoints)
        """
        all_funcs_ssa = {}
        internal_functions = []
        entrypoints = []
        
        # Process all functions to build SSA data
        for func_name, func_info in self.functions.items():
            function_node = self.function_map.get(func_name)
            if not function_node:
                continue
            
            # Create a function processor and get its SSA data
            func_processor = FunctionProcessor(func_name, func_info, function_node, self.function_map)
            func_data = func_processor.process()
            
            # Store in appropriate list based on visibility
            visibility = func_info.get("visibility", "")
            if visibility in ["external", "public"]:
                entrypoints.append(func_data)
            else:
                internal_functions.append(func_data)
            
            # Store for reference during inlining
            all_funcs_ssa[func_name] = func_data
            
        return all_funcs_ssa, internal_functions, entrypoints
        
    def _process_function_inlining(self, entrypoints, internal_functions):
        """
        Process function inlining for all functions.
        
        Args:
            entrypoints (list): List of entrypoint function data
            internal_functions (list): List of internal function data
        """
        # After processing all functions, perform inlining on each function
        for func_data in entrypoints + internal_functions:
            inliner = FunctionInliner(func_data, self.function_map, entrypoints + internal_functions)
            inliner.process()
            
    def _extract_call_information(self, entrypoints):
        """
        Extract additional call information using AST analysis.
        
        Args:
            entrypoints (list): List of entrypoint function data
        """
        # Extract function calls from the raw AST for better location information
        for entrypoint in entrypoints:
            # Get better location information from AST
            raw_calls = []
            raw_calls_seen = set()
            for statement in entrypoint["body_raw"]:
                extract_calls(statement, raw_calls, raw_calls_seen, self.function_map, self.source_text)
                
            # Combine with existing calls (preserve accurate locations)
            for raw_call in raw_calls:
                # Check if this call is already in the list
                for existing_call in entrypoint["calls"]:
                    if existing_call["name"] == raw_call["name"]:
                        # Update the location
                        existing_call["location"] = raw_call["location"]
                        break


class FunctionProcessor:
    """
    Handles processing of Solidity function definitions.
    """
    
    def __init__(self, func_name, func_info, function_node, function_map):
        """
        Initialize the function processor.
        
        Args:
            func_name (str): The function name
            func_info (dict): Function information dictionary
            function_node (ASTNode): The function definition AST node
            function_map (dict): Mapping of function names to ASTNodes
        """
        self.func_name = func_name
        self.func_info = func_info
        self.function_node = function_node
        self.function_map = function_map
        
    def process(self):
        """
        Process the function to build SSA data.
        
        Returns:
            dict: Function data dictionary with SSA information
        """
        # Extract function body and convert to SSA form
        body_raw = extract_function_body(self.function_node)
        ssa_data = self._convert_to_ssa_form(body_raw)
        
        # Create a function data record
        func_data = {
            "name": self.func_name,
            "location": self.func_info.get("location", [0, 0]),
            "visibility": self.func_info.get("visibility", ""),
            "calls": [],  # Will be filled later
            "body_raw": body_raw,
            "basic_blocks": ssa_data["blocks_with_phi"],
            "ssa": ssa_data["base_ssa_output"]
        }
        
        return func_data
        
    def _convert_to_ssa_form(self, body_raw):
        """
        Convert function body to SSA form.
        
        Args:
            body_raw (list): Raw statements from function body
            
        Returns:
            dict: SSA data dictionary
        """
        # Perform the SSA conversion pipeline
        statements_typed = classify_statements(body_raw)
        basic_blocks = split_into_basic_blocks(statements_typed)
        refined_blocks = refine_blocks_with_control_flow(basic_blocks)
        
        # Track variable accesses across blocks
        blocks_with_accesses = track_variable_accesses(refined_blocks)
        
        # Assign SSA versions to variable accesses
        blocks_with_ssa = SSAConverter.assign_ssa_versions(blocks_with_accesses)
        
        # Classify and add function calls
        blocks_with_calls = classify_and_add_calls(blocks_with_ssa, self.function_map)
        
        # Analyze loops with function calls for enhanced phi generation
        blocks_with_loop_calls = analyze_loop_calls(blocks_with_calls)
        
        # Insert phi functions at merge points
        blocks_with_phi = SSAConverter.insert_phi_functions(blocks_with_loop_calls)
        
        # Get the base SSA data before inlining (we'll finalize later)
        base_ssa_output = SSAConverter.integrate_ssa_output(blocks_with_phi)
        
        return {
            "blocks_with_phi": blocks_with_phi,
            "base_ssa_output": base_ssa_output
        }


class FunctionInliner:
    """
    Handles inlining of function calls within a function.
    """
    
    def __init__(self, func_data, function_map, all_functions):
        """
        Initialize the function inliner.
        
        Args:
            func_data (dict): Function data dictionary
            function_map (dict): Mapping of function names to ASTNodes
            all_functions (list): List of all function data dictionaries
        """
        self.func_data = func_data
        self.function_map = function_map
        self.all_functions = all_functions
        
    def process(self):
        """
        Process the function to inline function calls.
        """
        # Inline internal function calls
        blocks_with_inlined_calls = inline_internal_calls(
            self.func_data["basic_blocks"], 
            self.function_map, 
            self.all_functions
        )
        
        # Re-analyze blocks after inlining
        refined_blocks = self._refine_inlined_blocks(blocks_with_inlined_calls)
        
        # Clean up SSA statements
        blocks_with_clean_ssa = SSAConverter.cleanup_ssa_statements(refined_blocks)
        
        # Generate final SSA output with inlined calls
        ssa_output = SSAConverter.integrate_ssa_output(blocks_with_clean_ssa)
        
        # Update the function data with cleaned blocks
        self.func_data["basic_blocks"] = blocks_with_clean_ssa
        self.func_data["ssa"] = ssa_output
        
        # Extract and update function calls
        self._extract_function_calls()
        
    def _refine_inlined_blocks(self, blocks_with_inlined_calls):
        """
        Refine blocks after inlining to ensure proper structure.
        
        Args:
            blocks_with_inlined_calls (list): List of basic blocks with inlined calls
            
        Returns:
            list: Refined blocks with proper control flow
        """
        # Convert back to statements for re-splitting
        all_statements = self._convert_to_statements(blocks_with_inlined_calls)
        
        # If we have more than one statement, re-split the blocks
        if len(all_statements) <= 1:
            # If we just have one statement, finalize the original blocks
            return finalize_terminators(blocks_with_inlined_calls)
            
        # Create typed statements from the SSA statements for proper splitting
        statements_typed = self._create_typed_statements(all_statements)
        
        # Create new basic blocks with improved splitting
        new_basic_blocks = split_into_basic_blocks(statements_typed)
        
        # Apply control flow refinement to ensure proper structure
        refined_blocks = refine_blocks_with_control_flow(new_basic_blocks)
        
        # Copy back the original SSA statements to preserve the inlining
        self._restore_ssa_statements(refined_blocks, statements_typed, all_statements)
        
        # Recalculate block terminators
        return finalize_terminators(refined_blocks)
        
    def _convert_to_statements(self, blocks):
        """
        Convert SSA statements back to statement objects.
        
        Args:
            blocks (list): List of basic blocks with SSA statements
            
        Returns:
            list: List of statement objects
        """
        all_statements = []
        
        for block in blocks:
            # Convert each SSA statement back to a statement object
            for ssa_stmt in block.get("ssa_statements", []):
                # Skip original call statements that are duplicated
                if self._is_duplicate_call(ssa_stmt, block):
                    continue
                
                # Create a simplified statement node for re-splitting
                stmt_type = self._determine_statement_type(ssa_stmt)
                
                # Add to statements list
                all_statements.append({
                    "type": stmt_type,
                    "node": {"ssa": ssa_stmt}  # Store SSA for recovery
                })
                
        return all_statements
        
    def _is_duplicate_call(self, ssa_stmt, block):
        """
        Check if a statement is a duplicate call.
        
        Args:
            ssa_stmt (str): SSA statement
            block (dict): Block containing the statement
            
        Returns:
            bool: True if the statement is a duplicate call
        """
        if "call[internal](" not in ssa_stmt:
            return False
            
        # Check if this is a call statement that is duplicated
        return any(
            other_ssa.startswith(ssa_stmt.split(" = ")[0]) 
            for other_ssa in block.get("ssa_statements", []) 
            if other_ssa != ssa_stmt
        )
        
    def _determine_statement_type(self, ssa_stmt):
        """
        Determine the type of a statement from its SSA form.
        
        Args:
            ssa_stmt (str): SSA statement
            
        Returns:
            str: Statement type
        """
        if "return" in ssa_stmt:
            return "Return"
        elif "if" in ssa_stmt:
            return "IfStatement"
        elif "[" in ssa_stmt and "]" in ssa_stmt and ("+" in ssa_stmt or "-" in ssa_stmt):
            # Array/mapping updates should generally be block terminators
            return "FunctionCall"
        elif "=" in ssa_stmt and ("+" in ssa_stmt or "-" in ssa_stmt):
            # State variable modifications should generally be block terminators
            return "FunctionCall"
        else:
            return "Assignment"
            
    def _create_typed_statements(self, all_statements):
        """
        Create typed statements from SSA statements.
        
        Args:
            all_statements (list): List of statement objects
            
        Returns:
            list: List of typed statement objects
        """
        statements_typed = []
        
        for stmt in all_statements:
            ssa = stmt["node"]["ssa"]
            stmt_type = stmt["type"]
            
            # Treat state variable modifications as block terminators
            if "[" in ssa and "]" in ssa and ("+" in ssa or "-" in ssa):
                # Array/mapping state variable updates
                stmt_type = "FunctionCall"  # Force this to be a block terminator
            elif "=" in ssa and ("+" in ssa or "-" in ssa):
                # State variable modifications
                stmt_type = "FunctionCall"  # Force this to be a block terminator
            
            statements_typed.append({
                "type": stmt_type,
                "node": stmt["node"]
            })
            
        return statements_typed
        
    def _restore_ssa_statements(self, refined_blocks, statements_typed, all_statements):
        """
        Restore original SSA statements to the refined blocks.
        
        Args:
            refined_blocks (list): List of refined basic blocks
            statements_typed (list): List of typed statement objects
            all_statements (list): List of original statement objects
        """
        for block in refined_blocks:
            # Find the corresponding statements for this block
            block_statements = []
            
            for stmt_idx in range(len(statements_typed)):
                if stmt_idx < len(all_statements):
                    # Check if this statement belongs to the current block
                    stmt_in_block = False
                    
                    for block_stmt in block.get("statements", []):
                        if block_stmt.get("node", {}).get("ssa", "") == all_statements[stmt_idx]["node"]["ssa"]:
                            stmt_in_block = True
                            break
                    
                    if stmt_in_block:
                        block_statements.append(all_statements[stmt_idx]["node"]["ssa"])
            
            # If we found statements for this block, use them
            if block_statements:
                block["ssa_statements"] = block_statements
            
            # Update accesses based on the statements
            self._update_block_accesses(block, block_statements)
            
    def _update_block_accesses(self, block, block_statements):
        """
        Update block accesses based on the statements.
        
        Args:
            block (dict): Block to update
            block_statements (list): List of SSA statements
        """
        reads = set()
        writes = set()
        
        for ssa in block_statements:
            # Extract reads/writes from SSA statement
            if " = " in ssa:
                # This is a write
                lhs = ssa.split(" = ")[0]
                if "_" in lhs:
                    var_name = lhs.split("_")[0]
                    writes.add(var_name)
                    
                    # Check for indexed access like balanceOf[to]
                    if "[" in var_name and "]" in var_name:
                        base = var_name.split("[")[0]
                        writes.add(base)
                
                # Check for reads on right side
                rhs = ssa.split(" = ")[1]
                for part in rhs.split():
                    if "_" in part:
                        var_name = part.split("_")[0]
                        reads.add(var_name)
        
        # Clean up accesses by removing call markers
        reads_filtered = set(read for read in reads if not (
            "call[" in read or "call(" in read or ")" in read
        ))
        
        block["accesses"] = {"reads": list(reads_filtered), "writes": list(writes)}
        
    def _extract_function_calls(self):
        """
        Extract function calls information for reporting.
        """
        calls = []
        calls_seen = set()
        
        for block in self.func_data["basic_blocks"]:
            for stmt in block.get("ssa_statements", []):
                if "call[" in stmt:
                    if "call[internal]" in stmt:
                        # Extract internal call name
                        call_parts = stmt.split("call[internal](")[1].strip(")")
                        if "," in call_parts:
                            call_name = call_parts.split(",")[0].strip()
                        else:
                            call_name = call_parts.strip()
                            
                        if call_name not in calls_seen:
                            calls_seen.add(call_name)
                            
                            # Get source location for the function DEFINITION, not the call site
                            location = [0, 0]
                            if call_name in self.function_map:
                                # Get the function definition node
                                func_node = self.function_map[call_name]
                                src = func_node.get("src", "")
                                if src:
                                    try:
                                        # Convert source offset to line/col
                                        offset = int(src.split(":", 1)[0])
                                        location = offset_to_line_col(offset, '')  # No source text needed
                                    except (ValueError, IndexError):
                                        # Keep default [0, 0] if there's any error
                                        pass
                            
                            calls.append({
                                "name": call_name,
                                "in_contract": True,
                                "is_external": False,
                                "call_type": "internal",
                                "location": location  # This now points to the function definition
                            })
                    elif "call[external]" in stmt:
                        # Extract external call name
                        call_parts = stmt.split("call[external](")[1].strip(")")
                        if "," in call_parts:
                            call_name = call_parts.split(",")[0].strip()
                        else:
                            call_name = call_parts.strip()
                            
                        if call_name not in calls_seen:
                            calls_seen.add(call_name)
                            
                            # For external calls, we can't easily determine the location
                            # so we'll keep it as [0, 0] for now
                            calls.append({
                                "name": call_name,
                                "in_contract": False,
                                "is_external": True,
                                "call_type": "external",
                                "location": [0, 0]
                            })
        
        # Update the calls list
        self.func_data["calls"] = calls


def extract_function_body(node):
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


def extract_calls(node, calls, calls_seen, function_map, source_text):
    """
    Recursively extract function calls from an AST node.
    
    Args:
        node (dict): AST node to process
        calls (list): List to append call information to
        calls_seen (set): Set of already seen call names
        function_map (dict): Mapping of function names to their AST nodes
        source_text (str): Source code text
    """
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
                    line, col = offset_to_line_col(int(offsets), source_text)
                
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
                    line, col = offset_to_line_col(int(offsets), source_text)
                
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
            extract_calls(value, calls, calls_seen, function_map, source_text)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    extract_calls(item, calls, calls_seen, function_map, source_text)


# For backward compatibility
def finalize_terminators(basic_blocks):
    """
    Ensure all blocks have correct terminators for complete control flow.
    
    Args:
        basic_blocks (list): List of basic block dictionaries
        
    Returns:
        list: List of basic block dictionaries with updated terminators
    """
    from bsa.parser.control_flow import finalize_terminators
    return finalize_terminators(basic_blocks)