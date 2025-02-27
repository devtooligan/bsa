import click
import os
import subprocess
import glob
import json

class ASTNode:
    """Basic class to represent an AST node."""
    
    def __init__(self, node_data):
        """Initialize an ASTNode with the provided node data dictionary."""
        self.node_type = node_data.get("nodeType", "Unknown")
        self.data = node_data

@click.command()
@click.argument("path")
def main(path):
    print("BSA is running!")
    if not os.path.exists(path):
        print(f"Path does not exist: {path}")
        return

    try:
        # Run forge clean first
        subprocess.run(["forge", "clean"], cwd=path, check=True)
        
        # Then run forge build --ast
        subprocess.run(["forge", "build", "--ast"], cwd=path, check=True)
        print(f"Built ASTs in: {path}")
        
        # Find all .json files in the out/ directory
        out_dir = os.path.join(path, "out")
        ast_files = glob.glob(os.path.join(out_dir, "**/*.json"), recursive=True)
        print(f"Found {len(ast_files)} AST files")
        
        # Load the first AST file if any were found
        if ast_files:
            file_to_load = ast_files[0]
            print(f"Analyzing AST file: {file_to_load}")
            with open(file_to_load, "r") as f:
                ast_data = json.load(f)
                ast = ast_data.get("ast", {})
                
                # Parse the AST into an ASTNode object
                ast_node = ASTNode(ast)
                print(f"Parsed AST node with type: {ast_node.node_type}")
                
                # Get nodes list from the AST
                nodes = ast.get("nodes", [])
                
                # Parse each node in the nodes list into an ASTNode
                ast_nodes = []
                for node in nodes:
                    node_instance = ASTNode(node)
                    ast_nodes.append(node_instance)
                    print(f"Parsed node: {node_instance.node_type}")
                
                # Find external or public functions (Entrypoints) within contract definitions
                entrypoints = []
                for node in ast_nodes:
                    if node.node_type == "ContractDefinition":
                        # Get the contract's sub-nodes
                        contract_nodes = node.data.get("nodes", [])
                        for sub_node in contract_nodes:
                            if sub_node.get("nodeType") == "FunctionDefinition":
                                # Check function visibility
                                visibility = sub_node.get("visibility", "internal")
                                if visibility in ["external", "public"]:
                                    if "name" in sub_node:
                                        # Create entrypoint dictionary with name and body
                                        entrypoint = {
                                            "name": sub_node["name"],
                                            "body": sub_node.get("body", {})
                                        }
                                        entrypoints.append(entrypoint)
                
                # Process each entrypoint to find internal calls
                if entrypoints:
                    for entrypoint in entrypoints:
                        internal_calls = []
                        # Get the statements from the function body
                        statements = entrypoint["body"].get("statements", [])
                        
                        # Define a helper function to recursively find function calls
                        def find_function_calls(node):
                            calls = []
                            
                            # Check if this node is a function call
                            if node.get("nodeType") == "FunctionCall":
                                expression = node.get("expression", {})
                                if expression.get("nodeType") == "Identifier":
                                    if "name" in expression and expression["name"] not in ["require", "assert", "revert"]:
                                        calls.append(expression["name"])
                            
                            # Check arguments of function calls (for nested calls)
                            if node.get("nodeType") == "FunctionCall" and "arguments" in node:
                                for arg in node.get("arguments", []):
                                    calls.extend(find_function_calls(arg))
                            
                            # Check expression statements
                            if node.get("nodeType") == "ExpressionStatement" and "expression" in node:
                                calls.extend(find_function_calls(node["expression"]))
                                
                            return calls
                        
                        # Look for function calls in the statements
                        for statement in statements:
                            internal_calls.extend(find_function_calls(statement))
                        
                        # Print the entrypoint and its internal calls
                        print(f"Entrypoint: {entrypoint['name']}")
                        if internal_calls:
                            print(f"  Internal calls: {', '.join(internal_calls)}")
                        else:
                            print("  No internal calls")
                else:
                    print("No Entrypoints found")
                
                # Maintain backward compatibility with previous functionality
                # Extract contract name
                contract_name = "Unknown"
                for node in nodes:
                    if node.get("nodeType") == "ContractDefinition":
                        contract_name = node.get("name", "Unknown")
                        break
                
                print(f"Contract: {contract_name}")
        else:
            print("No AST files found")
        
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")

if __name__ == "__main__":
    main()