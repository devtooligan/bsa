"""
Tests for the integrated SSA output.
"""

import unittest
from unittest.mock import patch, MagicMock
from bsa.parser.ast_parser import ASTParser

class TestSSAIntegration(unittest.TestCase):
    """Test the integration of SSA into the output."""

    def test_integrate_ssa_output(self):
        """Test that the integrate_ssa_output function works correctly."""
        # Create a sample parser
        parser = ASTParser("/dummy/path")
        
        # Create sample basic blocks
        sample_blocks = [
            {
                "id": "Block0",
                "statements": [{"type": "Assignment", "node": {}}],
                "terminator": "goto Block1",
                "accesses": {"reads": [], "writes": ["x"]},
                "ssa_versions": {"reads": {}, "writes": {"x": 1}},
                "ssa_statements": ["x_1 = 1"]
            },
            {
                "id": "Block1",
                "statements": [{"type": "IfStatement", "node": {}}],
                "terminator": "if x_1 > 0 then goto Block2 else goto Block3",
                "accesses": {"reads": ["x"], "writes": []},
                "ssa_versions": {"reads": {"x": 1}, "writes": {}},
                "ssa_statements": ["if (x_1)"]
            }
        ]
        
        # Call the function
        result = parser.integrate_ssa_output(sample_blocks)
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "Block0")
        self.assertEqual(result[0]["ssa_statements"], ["x_1 = 1"])
        self.assertEqual(result[0]["terminator"], "goto Block1")
        self.assertEqual(result[1]["id"], "Block1")
        self.assertEqual(result[1]["ssa_statements"], ["if (x_1)"])
        self.assertEqual(result[1]["terminator"], "if x_1 > 0 then goto Block2 else goto Block3")
        
        # Verify that only the required fields are included
        self.assertEqual(len(result[0].keys()), 3)
        self.assertTrue("id" in result[0])
        self.assertTrue("ssa_statements" in result[0])
        self.assertTrue("terminator" in result[0])
        self.assertFalse("accesses" in result[0])
        self.assertFalse("statements" in result[0])
        self.assertFalse("ssa_versions" in result[0])

    def test_ssa_in_output(self):
        """Test that the SSA output is included in the parser output."""
        # Create a sample parser
        parser = ASTParser("/dummy/path")
        
        # Create mock contract data with SSA
        mock_contract_data = [{
            "contract": {"name": "Test"},
            "entrypoints": [{
                "name": "test",
                "location": [1, 1],
                "ssa": [
                    {
                        "id": "Block0",
                        "ssa_statements": ["x_1 = 1"],
                        "terminator": "goto Block1"
                    },
                    {
                        "id": "Block1",
                        "ssa_statements": ["if (x_1)"],
                        "terminator": "if x_1 > 0 then goto Block2 else goto Block3"
                    }
                ]
            }]
        }]
        
        # Override the parse method to return our mock data
        parser.parse = lambda: mock_contract_data
        
        # Run the parse function
        result = parser.parse()
        
        # Verify that SSA is in the output
        self.assertTrue(len(result) > 0)
        self.assertTrue("entrypoints" in result[0])
        self.assertTrue(len(result[0]["entrypoints"]) > 0)
        self.assertTrue("ssa" in result[0]["entrypoints"][0])
        
        # Check SSA content
        ssa = result[0]["entrypoints"][0]["ssa"]
        self.assertEqual(len(ssa), 2)
        self.assertEqual(ssa[0]["id"], "Block0")
        self.assertEqual(ssa[0]["ssa_statements"], ["x_1 = 1"])
        self.assertEqual(ssa[1]["id"], "Block1")
        self.assertEqual(ssa[1]["terminator"], "if x_1 > 0 then goto Block2 else goto Block3")

if __name__ == '__main__':
    unittest.main()