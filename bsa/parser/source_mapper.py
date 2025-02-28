"""
Source mapping utilities for translating Solidity AST source locations to file positions.
"""

def offset_to_line_col(offset, source_text, length=0):
    """
    Convert a byte offset to line and column numbers.
    
    Args:
        offset (int): The byte offset in the source
        source_text (str): The full source code text
        length (int, optional): The length of the segment. Defaults to 0.
        
    Returns:
        tuple: A tuple of (line_number, column_number)
    """
    # Handle empty source or invalid offsets
    if not source_text or offset < 0:
        return (1, 1)
        
    # Split the source into lines, preserving newline characters
    lines = source_text.splitlines(keepends=True)
    
    current_offset = 0
    line_num = 1
    
    for line in lines:
        # Use UTF-8 byte length for line length
        line_length = len(line.encode('utf-8'))
        
        # Check if the offset is within this line
        if current_offset <= offset < current_offset + line_length:
            # Calculate the column (offset relative to the start of the line)
            column = offset - current_offset + 1  # +1 because columns start at 1
            return (line_num, column)
        
        # Move to next line
        current_offset += line_length
        line_num += 1
    
    # Fallback if offset isn't found
    return (1, 1)