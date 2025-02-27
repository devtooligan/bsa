import os
import sys

def test_directory_structure():
    # Get the root directory (parent of the current tests directory)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Test that the package directory exists
    assert os.path.isdir(os.path.join(root_dir, 'bsa')), "Package directory 'bsa' does not exist"
    
    # Test that the tests directory exists
    assert os.path.isdir(os.path.join(root_dir, 'bsa', 'tests')), "Tests directory 'bsa/tests' does not exist"
    
    # Test that the virtual environment directory exists
    assert os.path.isdir(os.path.join(root_dir, '.venv')), "Virtual environment directory '.venv' does not exist"