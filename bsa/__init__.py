"""
Based Static Analyzer (BSA) - A static analyzer for Solidity smart contracts.

BSA is a tool for identifying security vulnerabilities in Solidity code.
It processes the Solidity AST to find patterns that might indicate vulnerabilities.
"""

__version__ = '0.1.0'

from bsa.parser import ASTNode, offset_to_line_col, ASTParser
from bsa.detectors import DetectorRegistry

__all__ = [
    'ASTNode',
    'offset_to_line_col',
    'ASTParser',
    'DetectorRegistry'
]