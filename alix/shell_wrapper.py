"""Shell wrapper functions for automatic usage tracking"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from alix.storage import AliasStorage


class ShellWrapper:
    """Creates shell wrapper functions that track alias usage automatically"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage = AliasStorage(storage_path)
    
    def generate_tracking_function(self, alias_name: str) -> str:
        """Generate a shell function that tracks usage and executes the alias"""
        alias = self.storage.get(alias_name)
        if not alias:
            return ""
        
        # Get the current working directory for context
        cwd_context = os.getcwd()
        
        # Create a tracking function that:
        # 1. Records the usage
        # 2. Executes the original command
        tracking_function = f"""
{alias_name}() {{
    # Track usage with alix
    alix track {alias_name} --context "cwd:{cwd_context}" >/dev/null 2>&1 &
    
    # Execute the original command
    {alias.command} "$@"
}}"""
        return tracking_function
    
    def generate_all_tracking_functions(self) -> str:
        """Generate tracking functions for all aliases"""
        aliases = self.storage.list_all()
        functions = []
        
        for alias in aliases:
            function = self.generate_tracking_function(alias.name)
            if function:
                functions.append(function)
        
        return "\n\n".join(functions)
    
    def generate_shell_integration_script(self, shell_type: str = "bash") -> str:
        """Generate a complete shell integration script"""
        if shell_type == "bash":
            return self._generate_bash_integration()
        elif shell_type == "zsh":
            return self._generate_zsh_integration()
        elif shell_type == "fish":
            return self._generate_fish_integration()
        else:
            return self._generate_bash_integration()  # Default to bash
    
    def _generate_bash_integration(self) -> str:
        """Generate bash integration script"""
        return f"""#!/bin/bash
# Alix CLI Usage Tracking Integration
# This script provides automatic usage tracking for aliases

# Function to track alias usage
track_alias_usage() {{
    local alias_name="$1"
    local context="$2"
    
    # Run tracking in background to avoid blocking
    alix track "$alias_name" --context "$context" >/dev/null 2>&1 &
}}

# Generate tracking functions for all aliases
{self.generate_all_tracking_functions()}

# Optional: Set up automatic tracking for existing aliases
# This can be customized based on user preferences
export ALIX_AUTO_TRACK=true

echo "Alix usage tracking enabled for {len(self.storage.list_all())} aliases"
"""
    
    def _generate_zsh_integration(self) -> str:
        """Generate zsh integration script"""
        return f"""#!/bin/zsh
# Alix CLI Usage Tracking Integration for Zsh
# This script provides automatic usage tracking for aliases

# Function to track alias usage
track_alias_usage() {{
    local alias_name="$1"
    local context="$2"
    
    # Run tracking in background to avoid blocking
    alix track "$alias_name" --context "$context" >/dev/null 2>&1 &
}}

# Generate tracking functions for all aliases
{self.generate_all_tracking_functions()}

# Optional: Set up automatic tracking for existing aliases
export ALIX_AUTO_TRACK=true

echo "Alix usage tracking enabled for {len(self.storage.list_all())} aliases"
"""
    
    def _generate_fish_integration(self) -> str:
        """Generate fish integration script"""
        # Fish has different syntax, so we need a different approach
        functions = []
        for alias in self.storage.list_all():
            functions.append(f"""function {alias.name}
    # Track usage
    alix track {alias.name} --context "cwd:{os.getcwd()}" >/dev/null 2>&1 &
    
    # Execute command
    {alias.command} $argv
end""")
        
        return f"""# Alix CLI Usage Tracking Integration for Fish
# This script provides automatic usage tracking for aliases

{chr(10).join(functions)}

echo "Alix usage tracking enabled for {len(self.storage.list_all())} aliases"
"""
    
    def install_tracking_integration(self, shell_config_path: Path, shell_type: str = "bash") -> bool:
        """Install tracking integration into shell config"""
        try:
            integration_script = self.generate_shell_integration_script(shell_type)
            
            # Add integration to shell config
            with open(shell_config_path, 'a') as f:
                f.write(f"\n\n# Alix CLI Usage Tracking Integration\n")
                f.write(f"# Added on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(integration_script)
            
            return True
        except Exception:
            return False
    
    def create_standalone_tracking_script(self, output_path: Path, shell_type: str = "bash") -> bool:
        """Create a standalone tracking script"""
        try:
            integration_script = self.generate_shell_integration_script(shell_type)
            
            # Ensure the parent directory exists (only if it doesn't exist)
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(integration_script)
            
            # Make it executable
            os.chmod(output_path, 0o755)
            return True
        except Exception as e:
            # For debugging purposes, you might want to log the exception
            # print(f"Error creating standalone tracking script: {e}")
            return False
