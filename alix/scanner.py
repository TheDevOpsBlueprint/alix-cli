"""Scanner for existing system aliases"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict

from alix.models import Alias
from alix.shell_detector import ShellDetector, ShellType


class AliasScanner:
    """Scan and import existing aliases from shell configuration"""

    # Regex pattern to match alias definitions
    ALIAS_PATTERN = re.compile(
        r"^\s*alias\s+([a-zA-Z_][a-zA-Z0-9_\-]*)\s*=\s*['\"]?(.+?)['\"]?\s*$",
        re.MULTILINE,
    )

    def __init__(self):
        self.detector = ShellDetector()

    def scan_file(self, filepath: Path) -> List[Alias]:
        """Scan a single file for aliases"""
        aliases = []
        if not filepath.exists():
            return aliases

        try:
            content = filepath.read_text()
            matches = self.ALIAS_PATTERN.findall(content)

            for name, command in matches:
                # Clean up command (remove quotes if present)
                command = command.strip("'\"")
                alias = Alias(
                    name=name,
                    command=command,
                    description=f"Imported from {filepath.name}",
                )
                aliases.append(alias)
        except Exception:  # pragma: no cover
            pass

        return aliases

    def scan_system(self) -> Dict[str, List[Alias]]:
        """Scan all shell config files for aliases"""
        shell_type = self.detector.detect_current_shell()
        config_files = self.detector.find_config_files(shell_type)

        results = {}
        for filename, filepath in config_files.items():
            aliases = self.scan_file(filepath)
            if aliases:  # pragma: no branch
                results[filename] = aliases

        return results

    def get_active_aliases(self) -> List[Alias]:
        """Get currently active aliases using shell command"""
        aliases = []
        try:
            shell_type = self.detector.detect_current_shell()
            if shell_type == ShellType.UNKNOWN:
                return []
            # Run alias command to get current aliases
            result = subprocess.run(
                [shell_type.value, "-i", "-c", "alias"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    match = self.ALIAS_PATTERN.match(line)
                    if match:
                        name, command = match.groups()
                        aliases.append(
                            Alias(
                                name=name,
                                command=command.strip("'\""),
                                description="Active system alias",
                            )
                        )
        except Exception:  # pragma: nocover
            pass

        return aliases
