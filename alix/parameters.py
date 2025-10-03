"""Parameter parsing and validation utilities for aliases"""

import re
from typing import List, Dict, Tuple, Optional


class ParameterParser:
    """Parse and validate command parameters in aliases"""

    # Regex patterns for different parameter types
    POSITIONAL_PATTERN = r'\$(\d+)'  # Matches $1, $2, $3, etc.
    ALL_ARGS_PATTERN = r'\$@'  # Matches $@
    ALL_ARGS_STRING_PATTERN = r'\$\*'  # Matches $*
    
    @staticmethod
    def extract_parameters(command: str) -> List[str]:
        """Extract all parameter placeholders from a command
        
        Args:
            command: The command string to parse
            
        Returns:
            List of unique parameter placeholders found (e.g., ['$1', '$2', '$@'])
        """
        params = set()
        
        # Find positional parameters
        for match in re.finditer(ParameterParser.POSITIONAL_PATTERN, command):
            params.add(f"${match.group(1)}")
        
        # Find special parameters
        if re.search(ParameterParser.ALL_ARGS_PATTERN, command):
            params.add('$@')
        if re.search(ParameterParser.ALL_ARGS_STRING_PATTERN, command):
            params.add('$*')
        
        # Sort positional parameters numerically
        positional = sorted([p for p in params if p[1:].isdigit()], 
                          key=lambda x: int(x[1:]))
        special = sorted([p for p in params if not p[1:].isdigit()])
        
        return positional + special
    
    @staticmethod
    def get_max_parameter_index(command: str) -> int:
        """Get the highest parameter index used in the command
        
        Args:
            command: The command string to parse
            
        Returns:
            The highest parameter number, or 0 if no parameters
        """
        matches = re.findall(ParameterParser.POSITIONAL_PATTERN, command)
        if not matches:
            return 0
        return max([int(m) for m in matches])
    
    @staticmethod
    def has_parameters(command: str) -> bool:
        """Check if a command uses any parameters
        
        Args:
            command: The command string to check
            
        Returns:
            True if the command uses parameters
        """
        return bool(re.search(r'\$\d+|\$@|\$\*', command))
    
    @staticmethod
    def validate_parameters(command: str) -> Tuple[bool, Optional[str]]:
        """Validate parameter usage in a command
        
        Args:
            command: The command string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ParameterParser.has_parameters(command):
            return True, None
        
        # Check for sequential parameters
        matches = re.findall(ParameterParser.POSITIONAL_PATTERN, command)
        if matches:
            param_numbers = sorted(set(int(m) for m in matches))
            
            # Check if parameters start at 1
            if param_numbers[0] != 1:
                return False, "Parameters should start at $1"
            
            # Check for gaps in parameter sequence
            for i in range(len(param_numbers) - 1):
                if param_numbers[i + 1] - param_numbers[i] > 1:
                    missing = param_numbers[i] + 1
                    return False, f"Missing parameter ${missing} in sequence"
        
        return True, None
    
    @staticmethod
    def get_parameter_description(param: str, descriptions: Dict[str, str]) -> str:
        """Get a human-readable description for a parameter
        
        Args:
            param: The parameter placeholder (e.g., '$1')
            descriptions: Dictionary mapping parameters to descriptions
            
        Returns:
            Description string or generic placeholder
        """
        if param in descriptions:
            return descriptions[param]
        
        # Default descriptions for special parameters
        if param == '$@':
            return 'all arguments'
        if param == '$*':
            return 'all arguments as string'
        
        # Generic description for positional parameters
        param_num = param[1:]
        return f'arg{param_num}'
    
    @staticmethod
    def generate_usage_example(name: str, command: str, 
                               descriptions: Optional[Dict[str, str]] = None) -> str:
        """Generate a usage example with parameter hints
        
        Args:
            name: The alias name
            command: The command with parameters
            descriptions: Optional parameter descriptions
            
        Returns:
            Usage example string (e.g., 'myalias <file> <output>')
        """
        if not ParameterParser.has_parameters(command):
            return name
        
        descriptions = descriptions or {}
        params = ParameterParser.extract_parameters(command)
        
        param_hints = []
        for param in params:
            desc = ParameterParser.get_parameter_description(param, descriptions)
            param_hints.append(f"<{desc}>")
        
        return f"{name} {' '.join(param_hints)}"
    
    @staticmethod
    def auto_detect_parameter_descriptions(command: str) -> Dict[str, str]:
        """Attempt to auto-detect parameter descriptions from command context
        
        Args:
            command: The command string to analyze
            
        Returns:
            Dictionary mapping parameters to suggested descriptions
        """
        descriptions = {}
        params = ParameterParser.extract_parameters(command)
        
        # Common patterns that might indicate parameter purpose
        patterns = {
            r'cp.*\$1.*\$2': {
                '$1': 'source',
                '$2': 'destination'
            },
            r'mv.*\$1.*\$2': {
                '$1': 'source',
                '$2': 'destination'
            },
            r'git\s+commit.*\$1': {
                '$1': 'message'
            },
            r'docker\s+run.*\$1': {
                '$1': 'image'
            },
            r'ssh.*\$1': {
                '$1': 'host'
            },
            r'curl.*\$1': {
                '$1': 'url'
            },
            r'echo.*\$1': {
                '$1': 'message'
            },
            r'cat.*\$1': {
                '$1': 'file'
            },
            r'grep.*\$1.*\$2': {
                '$1': 'pattern',
                '$2': 'file'
            },
        }
        
        for pattern, param_desc in patterns.items():
            if re.search(pattern, command):
                for param in params:
                    if param in param_desc:
                        descriptions[param] = param_desc[param]
        
        return descriptions
