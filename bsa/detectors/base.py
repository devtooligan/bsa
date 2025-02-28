"""
Base detector classes for BSA vulnerability detection.
"""

class Detector:
    """Base class for all vulnerability detectors."""
    
    def __init__(self, name="BaseDetector"):
        """Initialize the detector with a name.
        
        Args:
            name (str): Name of the detector
        """
        self.name = name
        self.findings = []
    
    def detect(self, contract_data):
        """
        Run the detection algorithm and return findings.
        
        Args:
            contract_data (dict): Contract data for analysis
            
        Returns:
            list: List of findings
        """
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement this method")
    
    def add_finding(self, finding):
        """
        Add a finding to the detector's findings list.
        
        Args:
            finding (dict): Finding details
        """
        self.findings.append(finding)
    
    def report(self):
        """
        Format findings for output.
        
        Returns:
            list: List of formatted finding reports
        """
        reports = []
        for finding in self.findings:
            reports.append(self._format_finding(finding))
        return reports
    
    def _format_finding(self, finding):
        """
        Format a finding for output.
        
        Args:
            finding (dict): Finding details
            
        Returns:
            str: Formatted finding report
        """
        contract_name = finding.get("contract_name", "Unknown")
        function_name = finding.get("function_name", "Unknown")
        description = finding.get("description", "")
        
        return f"{self.name.upper()} found in {contract_name}.{function_name}: {description}"