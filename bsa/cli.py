"""
Based Static Analyzer (BSA) CLI.

This module provides the command-line interface for BSA, a tool for analyzing
Solidity smart contracts for vulnerabilities.
"""

import click
import os

from bsa.parser.ast_parser import ASTParser
from bsa.detectors import DetectorRegistry
from bsa.parser.nodes import ASTNode
from bsa.parser.source_mapper import offset_to_line_col

# For backward compatibility with tests
contract_output = []

@click.command()
@click.argument("path")
def main(path):
    """
    Run BSA analysis on a Solidity project.
    
    PATH is the path to the project root.
    """
    if not os.path.exists(path):
        print(f"Path does not exist: {path}")
        # Set global variable for testing
        contract_output.clear()
        return []
    
    try:
        # Initialize parser with debug enabled
        import traceback
        parser = ASTParser(path)
        
        # Generate and parse AST
        contract_data_list = parser.parse()
        
        # Remove duplicate entries in contract_data_list to avoid processing the same contract multiple times
        unique_contracts = {}
        for contract_data in contract_data_list:
            contract_name = contract_data.get("contract", {}).get("name", "Unknown")
            # Only keep the first instance of each contract
            if contract_name not in unique_contracts:
                unique_contracts[contract_name] = contract_data
        
        # Replace the original list with deduplicated data
        contract_data_list = list(unique_contracts.values())
        
        # Ensure we have data
        if not contract_data_list:
            print("No src/ AST files found")
            # Set global variable for testing
            contract_output.clear()
            return []
            
    except Exception as e:
        print(f"Parser initialization failed: {e}")
        traceback.print_exc()
        return []
        
    try:
        
        # Output each contract's details
        for contract_data in contract_data_list:
            contract = contract_data.get("contract", {})
            entrypoints = contract_data.get("entrypoints", [])
            
            # Print contract information
            print(f"Contract: {contract.get('name', 'Unknown')}")
            
            # Print each entrypoint
            if entrypoints:
                for entrypoint in entrypoints:
                    try:
                        name = entrypoint.get("name", "Unknown")
                        line, col = entrypoint.get("location", [0, 0])
                        
                        # Print entrypoint information
                        print(f"Entrypoint: {name} at line {line}, col {col}")
                        
                        # Print SSA analysis information
                        basic_blocks = entrypoint.get("basic_blocks", [])
                        ssa_blocks = entrypoint.get("ssa", [])
                        print(f"  Blocks: {len(basic_blocks)}")
                        print(f"  SSA Blocks: {len(ssa_blocks)}")
                        
                        # Print detailed SSA block information
                        try:
                            if ssa_blocks:
                                print("  SSA Blocks:")
                                for block in ssa_blocks:
                                    block_id = block.get("id", "Unknown")
                                    ssa_statements = block.get("ssa_statements", [])
                                    terminator = block.get("terminator", "Unknown")
                                    reads = block.get("accesses", {}).get("reads", [])
                                    writes = block.get("accesses", {}).get("writes", [])
                                    
                                    print(f"    Block {block_id}:")
                                    print(f"      SSA: {ssa_statements}")
                                    print(f"      Terminator: {terminator}")
                                    print(f"      Accesses: reads={reads}, writes={writes}")
                        except (TypeError, AttributeError, IndexError) as e:
                            print(f"    Error displaying SSA blocks: {str(e)}")
                        
                        # Print detailed variable accesses by block
                        try:
                            print("  Variable Accesses:")
                            for block in ssa_blocks:
                                block_id = block.get("id", "Unknown")
                                reads = block.get("accesses", {}).get("reads", [])
                                writes = block.get("accesses", {}).get("writes", [])
                                print(f"    Block {block_id}: reads={reads}, writes={writes}")
                        except (TypeError, AttributeError) as e:
                            print(f"    Error calculating variable accesses: {str(e)}")
                    except Exception as e:
                        print(f"  Error processing entrypoint: {str(e)}")
                    
                    # Print function calls, separated by type
                    all_calls = entrypoint.get("calls", [])
                    if all_calls:
                        # Separate into internal and external calls
                        internal_calls = []
                        external_calls = []
                        
                        for call in all_calls:
                            call_line, call_col = call.get("location", [0, 0])
                            call_type = call.get("call_type", "unknown")
                            scope = "this contract" if call.get("in_contract", False) else "unknown"
                            
                            call_info = f"{call.get('name', 'unknown')} ({scope}) at line {call_line}, col {call_col}"
                            
                            # Categorize based on call type
                            if call.get("is_external", False) or call_type in ["external", "low_level_external", "delegatecall", "staticcall"]:
                                external_calls.append(call_info)
                            else:
                                internal_calls.append(call_info)
                        
                        # Print internal calls
                        if internal_calls:
                            print(f"  Internal calls: {', '.join(internal_calls)}")
                        else:
                            print("  No internal calls")
                            
                        # Print external calls
                        if external_calls:
                            print(f"  External calls: {', '.join(external_calls)}")
                    else:
                        print("  No function calls")
            else:
                print("No Entrypoints found in src/ files")
        
        # Run detectors
        try:
            registry = DetectorRegistry()
            all_findings = registry.run_all(contract_data_list)
            
            # Print detector findings with deduplication
            for detector_name, findings in all_findings.items():
                # Use a set to track unique findings
                seen_findings = set()
                
                for finding in findings:
                    contract_name = finding.get("contract_name", "Unknown")
                    function_name = finding.get("function_name", "Unknown")
                    
                    # Create a unique key for this finding to deduplicate
                    finding_key = f"{contract_name}.{function_name}"
                    
                    # Only process this finding if we haven't seen it before
                    if finding_key not in seen_findings:
                        seen_findings.add(finding_key)
                        
                        desc = finding.get("description", "")
                        sev = finding.get("severity", "")
                        print(f"!!!! {detector_name.upper()} found in {contract_name}.{function_name}")
                        print(f"     Description: {desc}")
                        print(f"     Severity: {sev}")
        except Exception as e:
            print(f"Detector error: {e}")
            traceback.print_exc()
        
        # Store output for testing
        contract_output.clear()
        contract_output.extend(contract_data_list)
        
        return contract_data_list
        
    except Exception as e:
        print(f"Command failed: {e}")
        traceback.print_exc()
        return []

if __name__ == "__main__":
    main()