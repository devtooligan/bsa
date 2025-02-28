"""
Registry for BSA vulnerability detectors.
"""

from bsa.detectors.reentrancy import ReentrancyDetector

class DetectorRegistry:
    """Registry for vulnerability detectors."""
    
    def __init__(self):
        """Initialize the detector registry with available detectors."""
        self.detectors = {}
        # Initialize and register built-in detectors
        self.register_detector("reentrancy", ReentrancyDetector())
    
    def register_detector(self, name, detector):
        """
        Register a detector with the registry.
        
        Args:
            name (str): Name for the detector
            detector: Detector instance
        """
        self.detectors[name] = detector
    
    def get_detector(self, name):
        """
        Get a detector by name.
        
        Args:
            name (str): Name of the detector
            
        Returns:
            Detector: The detector instance or None if not found
        """
        return self.detectors.get(name)
    
    def get_available_detectors(self):
        """
        Get a list of available detector names.
        
        Returns:
            list: List of detector names
        """
        return list(self.detectors.keys())
    
    def run_detector(self, name, contract_data):
        """
        Run a specific detector by name.
        
        Args:
            name (str): Name of the detector
            contract_data (dict): Contract data for analysis
            
        Returns:
            list: List of findings
            
        Raises:
            ValueError: If the detector is not found
        """
        detector = self.get_detector(name)
        if detector is None:
            raise ValueError(f"Detector '{name}' not found")
        
        return detector.detect(contract_data)
    
    def run_all(self, contract_data_list):
        """
        Run all registered detectors on the contract data.
        
        Args:
            contract_data_list (list): List of contract data for analysis
            
        Returns:
            dict: Dictionary of detector name to list of findings
        """
        all_findings = {}
        
        for name, detector in self.detectors.items():
            all_findings[name] = []
            
            for contract_data in contract_data_list:
                all_findings[name].extend(detector.detect(contract_data))
        
        return all_findings