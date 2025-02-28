# BasedSSA Technical Specification

## Overview
BasedSSA is a full-featured Static Single Assignment (SSA) representation for Solidity smart contracts, derived from Foundry's `forge build --ast` AST JSON output. It models intra-procedural data flow with complete control flow support, including basic blocks and phi-functions, to enable precise analysis within the Based Static Analyzer (BSA).

## Key Features
- **Full Control Flow**: Represents conditionals, loops, and jumps using basic blocks and phi-functions.
- **Solidity-Specific**: Captures state variables, internal/external calls, and low-level operations (`call`, `delegatecall`, `staticcall`).
- **Intra-Procedural Scope**: Focuses on single-function analysis, with hooks for future inter-procedural expansion.

## Structure
For each contract, BasedSSA maps function names to their SSA representations, structured as:

- **Basic Blocks**: A list of blocks representing the function's control flow. Each block contains:
  - **Phi-Functions**: At the block's start, reconciling variables from multiple paths (e.g., `stateVar_3 = phi(stateVar_1, stateVar_2)`).
  - **Statements**: SSA statements like:
    - **Assignments**: `var_version = expression` (e.g., `x_1 = y_0 + 5`).
    - **Calls**: `return_var_version = call(target, args)` with detailed call type info.
    - **Control Flow**: Jumps or conditional jumps (e.g., `if cond_1 then goto block2 else goto block3`).
  - **Terminator**: Ends with a jump, conditional jump, or return.

- **Variable Versions**:
  - **Local Variables**: Unique versions per assignment (e.g., `x_0`, `x_1`).
  - **State Variables**: Versioned within the function (e.g., `stateVar_0`, `stateVar_1`), treated as persistent but scoped to intra-procedural analysis.

### Call Handling
- **Internal Calls**: `return_var_version = call(internal_function, args)`, with a summary of modified state vars.
- **External Calls**:
  - **Known Contracts**: Analyzed like internal calls if code is available.
  - **Unknown Contracts**: Assumed to modify all state and return arbitrary data.
- **Low-Level Calls**:
  - `call`: Can modify state and return data.
  - `delegatecall`: Executes in caller's context, affecting caller's state.
  - `staticcall`: Read-only, flagged as state-safe.

## Integration with BSA
- **Input**: Parsed from Foundry AST JSON.
- **Output**: Stored in BSA's dictionary under each entrypoint as an `ssa` field (e.g., `entrypoints[i]["ssa"] = [block_list]`).

## Example
For this Solidity function:
```solidity
uint stateVar;
function example(uint x) public {
    stateVar = x;
    if (x > 0) {
        stateVar = stateVar + 1;
    }
}
```

BasedSSA representation:
```
* Block 0:
   * stateVar_1 = x_0
   * cond_1 = x_0 > 0
   * if cond_1 then goto Block 1 else goto Block 2
* Block 1:
   * stateVar_2 = stateVar_1 + 1
   * goto Block 2
* Block 2:
   * stateVar_3 = phi(stateVar_1, stateVar_2)
   * return
```

## Extensibility
* **Modular Blocks**: Basic block structure allows adding inter-procedural links (e.g., call inlining) later.
* **Metadata Hooks**: Each statement can accept additional fields (e.g., privileged labels) without breaking the format.
* **Scalable Calls**: Call summaries can evolve to include detailed effects as inter-procedural analysis is added.

## Assumptions
* **Intra-Procedural**: State variable versions reset per function; cross-function persistence is a future step.
* **Conservative Calls**: External calls to unknown contracts assume maximal impact.

## Revised Complete List of Baby Steps for Implementing BasedSSA

Each step is scoped to be concise (targeting <100 LOC) and ends with a test. These build on your existing BSA parser.

1. Parse Full Function Body from AST
   * Extract the body node's statements list from each FunctionDefinition in the AST JSON and store it raw.
   * Test: Verify the raw body is captured for a sample function.

2. Classify Statement Types
   * Categorize each statement in the body into basic types (e.g., Assignment, FunctionCall, IfStatement).
   * Test: Check that statements are correctly typed for a simple function.

3. Split into Initial Basic Blocks
   * Divide the statement list into basic blocks based on linear execution (no control flow yet).
   * Test: Ensure blocks are created and contain the right statements.

4. Handle Control Flow Splits
   * Adjust blocks for IfStatement nodes, creating true/false branches with jumps.
   * Test: Validate block structure for a function with an if.

5. Track Variable Reads and Writes
   * Build a function to log variable reads/writes in each statement.
   * Test: Confirm reads/writes are identified correctly.

6. Assign SSA Variable Versions
   * Version variables in each block (e.g., x_0, x_1) based on writes.
   * Test: Check versioning for a sequence of assignments.

7. Classify and Add Function Calls
   * Tag calls as internal, high_level_external, etc., and add them as SSA statements.
   * Test: Verify call classification and SSA format.

8. Insert Phi-Functions at Merges
   * Add phi-functions at block merge points for variables with multiple definitions.
   * Test: Ensure phi-functions appear correctly after an if.

9. Finalize Block Terminators
   * Set proper terminators (jumps, returns) for each block.
   * Test: Confirm terminators link blocks as expected.

10. Integrate SSA into BSA Output
    * Add the SSA block list to each entrypoint's output dict.
    * Test: Validate SSA field in the final output.