"""
BSA parser module for working with Solidity ASTs.
"""

from bsa.parser.nodes import ASTNode
from bsa.parser.source_mapper import offset_to_line_col
from bsa.parser.parser_core import ASTParser
from bsa.parser.basic_blocks import classify_statements, split_into_basic_blocks
from bsa.parser.control_flow import refine_blocks_with_control_flow
from bsa.parser.variable_tracking import track_variable_accesses
from bsa.parser.function_calls import classify_and_add_calls as classify_function_calls, inline_internal_calls
from bsa.parser.loop_analysis import analyze_loop_calls
from bsa.parser.ssa_conversion import SSAConverter, convert_to_ssa

__all__ = [
    'ASTNode',
    'offset_to_line_col',
    'ASTParser',
    'classify_statements',
    'split_into_basic_blocks',
    'refine_blocks_with_control_flow',
    'track_variable_accesses',
    'classify_function_calls',
    'inline_internal_calls',
    'analyze_loop_calls',
    'SSAConverter',
    'convert_to_ssa'
]