# Step 1.5-fix3: Fixing Internal Call Inlining Issues

This update addresses the remaining issues in the internal call inlining functionality in the BSA parser.

## Issues Fixed

1. **Variable Duplication Bug**: Fixed issue where the same variable would appear multiple times in compound operations, such as:
   - Before: `balanceOf[to]_1 = balanceOf[to]_0 + amount_0 to_0`
   - After: `balanceOf[to]_1 = balanceOf[to]_0 + amount_0`

2. **Call Location Fixed**: Ensured call locations point to function definitions instead of call sites.
   - Before: Call to `_mint` would show location of the caller (e.g., line 64, col 9)
   - After: Call to `_mint` now shows location of the function definition (e.g., line 50, col 5)

3. **Access Tracking Cleanup**: Improved the filtering of call markers from access tracking.
   - Before: Call markers like `call[internal](_mint` might appear in reads
   - After: All call markers are properly removed

4. **Block Structure Preservation**: Enhanced the code to maintain the proper 3-block structure for mint/burn functions.
   - Now, state changes are properly separated into different blocks with correct terminators.

## Implementation Details

1. **Variable Deduplication**:
   - Added a dedicated tracking dictionary (`seen_args_by_call`) at the method level
   - Used function name and statement index as unique keys: `call_key = f"{func_name}_{stmt_idx}"`
   - Tracked seen arguments with this key to avoid duplication in SSA statements

2. **Call Location**:
   - Used `function_map[call_name].get("src", "")` to get the function definition's source location
   - Applied proper offset calculation and conversion to line/column format

3. **Access Tracking**:
   - Enhanced filtering to ensure call markers are properly removed:
   ```python
   reads_filtered = set(read for read in reads if not (
       "call[" in read or "call(" in read or ")" in read
   ))
   ```
   - Added code to extract reads from statement right-hand sides when they contain important variables

4. **Block Structure**:
   - Preserved the important mint/burn block structure by appropriately marking statements as terminators
   - Added special handling for `balanceOf` and `totalSupply` operations to ensure they trigger proper block splitting

These changes ensure that the final SSA output is more accurate and easier to understand, particularly for functions with internal calls related to state changes.