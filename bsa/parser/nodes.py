"""
BSA Node classes for working with AST representation.
"""

class ASTNode:
    """Basic class to represent an AST node."""
    
    def __init__(self, node_data):
        """Initialize an ASTNode with the provided node data dictionary."""
        self.node_type = node_data.get("nodeType", "Unknown")
        self.data = node_data
        self.source = node_data.get("src", "0:0:0")
    
    def get(self, key, default=None):
        """Helper method to access node data.
        
        Args:
            key (str): The key to lookup in the node data
            default: The default value to return if key is not found
            
        Returns:
            The value from node data or the default
        """
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        """Dictionary-style access to node data.
        
        Args:
            key (str): The key to lookup in the node data
            
        Returns:
            The value from node data
            
        Raises:
            KeyError: If the key is not found
        """
        return self.data[key]
    
    def __contains__(self, key):
        """Check if a key exists in node data.
        
        Args:
            key (str): The key to check
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        return key in self.data