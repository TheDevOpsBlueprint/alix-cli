import pytest
import sys
import subprocess
from unittest.mock import Mock, patch
from pathlib import Path
from alix.shell_detector import ShellDetector, ShellType


@pytest.fixture
def shell_detector():
    """Fixture for ShellDetector instance"""
    return ShellDetector()


@pytest.fixture
def mock_home_dir(tmp_path):
    """Fixture for a mock home directory"""
    return tmp_path / "home"


@pytest.fixture
def isolated_shell_detector(shell_detector):
    """Fixture for ShellDetector with common isolation patches"""
    with patch.dict('os.environ', {}, clear=True), \
         patch('pwd.getpwuid', side_effect=KeyError), \
         patch('psutil.Process', side_effect=ImportError), \
         patch('subprocess.run', side_effect=Exception), \
         patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
        yield shell_detector


class TestShellDetector:
    """Unit tests for ShellDetector class covering initialization, shell detection methods, and config file handling"""

    class TestInit:
        """Tests for ShellDetector initialization and home directory handling"""

        def test_init_without_home_dir(self):
            """Test initialization without providing home_dir"""
            with patch('pathlib.Path.home', return_value=Path('/mock/home')):
                detector = ShellDetector()
                assert detector.home_dir == Path('/mock/home')

        def test_init_with_home_dir(self):
            """Test initialization with provided home_dir"""
            custom_home = Path('/custom/home')
            detector = ShellDetector(home_dir=custom_home)
            assert detector.home_dir == custom_home


        def test_init_home_dir_permission_denied(self):
            """Test initialization when home directory access is denied"""
            with patch('pathlib.Path.home', side_effect=PermissionError):
                with pytest.raises(PermissionError):
                    ShellDetector()

    class TestDetectCurrentShell:
        """Tests for shell detection via various methods: SHELL env, passwd, parent process, config hints, and platform-specific detection"""

        @pytest.mark.parametrize("shell_env,expected", [
            ("/bin/zsh", ShellType.ZSH),
            ("/usr/bin/bash", ShellType.BASH),
            ("/usr/local/bin/fish", ShellType.FISH),
            ("/bin/sh", ShellType.SH),
        ])
        def test_detect_via_shell_env(self, shell_detector, shell_env, expected):
            """Test detection via SHELL environment variable"""
            with patch.dict('os.environ', {'SHELL': shell_env}, clear=True):
                result = shell_detector.detect_current_shell()
                assert result == expected


        @pytest.mark.parametrize("shell_path,expected", [
            ('/bin/zsh', ShellType.ZSH),
            ('/bin/bash', ShellType.BASH),
            ('/usr/bin/fish', ShellType.FISH),
            ('/bin/sh', ShellType.SH),
            ('/usr/bin/sh', ShellType.SH),
        ])
        def test_detect_via_passwd(self, shell_detector, shell_path, expected):
            """Test detection via /etc/passwd for various shells"""
            with patch('pwd.getpwuid') as mock_pwd, \
                 patch('os.getuid', return_value=1000), \
                 patch.dict('os.environ', {}, clear=True):
                mock_pwd.return_value.pw_shell = shell_path
                result = shell_detector.detect_current_shell()
                assert result == expected


        # pwd module edge cases
        @pytest.mark.parametrize("pwd_result,expected", [
            (None, ShellType.UNKNOWN),
            (Mock(pw_shell=12345), ShellType.UNKNOWN),  # Non-string
            (Mock(spec=[]), ShellType.UNKNOWN),  # No pw_shell attribute
        ])
        def test_detect_via_passwd_edge_cases(self, shell_detector, pwd_result, expected):
            """Test pwd.getpwuid returning various edge case results"""
            with patch.dict('os.environ', {'SHELL': ''}, clear=True), \
                 patch('pwd.getpwuid', return_value=pwd_result), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch('subprocess.run', side_effect=Exception), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                result = shell_detector.detect_current_shell()
                assert result == expected

        @pytest.mark.parametrize("exception", [OSError, PermissionError, RuntimeError, ValueError])
        def test_detect_via_passwd_different_exceptions(self, shell_detector, exception):
            """Test pwd.getpwuid raising different exceptions"""
            with patch.dict('os.environ', {'SHELL': ''}, clear=True), \
                 patch('pwd.getpwuid', side_effect=exception), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch('subprocess.run', side_effect=Exception), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                # The exception should be caught and the method should continue
                result = shell_detector.detect_current_shell()
                assert result == ShellType.UNKNOWN

        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        @pytest.mark.parametrize("shell_path,expected", [
            ('/bin/zsh', ShellType.ZSH),
            ('/bin/bash', ShellType.BASH),
            ('/usr/bin/fish', ShellType.FISH),
            ('/bin/sh', ShellType.SH),
        ])
        def test_detect_via_dscl(self, shell_detector, shell_path, expected):
            """Test detection via dscl on macOS for various shells"""
            with patch('sys.platform', 'darwin'), \
                 patch('os.getenv', return_value='user'), \
                 patch('subprocess.run') as mock_run, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_run.return_value = Mock(returncode=0, stdout=f'UserShell: {shell_path}\n')
                result = shell_detector.detect_current_shell()
                assert result == expected



        # Subprocess edge cases for dscl and sw_vers
        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        @pytest.mark.parametrize("dscl_output,expected", [
            ('', ShellType.UNKNOWN),
            ('UserShell\n', ShellType.UNKNOWN),  # Missing value after colon
            ('SomeOtherKey: value\nUserShell: /bin/zsh\n', ShellType.ZSH),  # Unexpected format but parses correctly
            ('SomeOtherKey: value\n', ShellType.UNKNOWN),  # No UserShell line
            ('UserShell: /bin/sh\n', ShellType.SH),  # Test sh detection
            ('UserShell: /bin/sh', ShellType.SH),  # No newline
        ])
        def test_detect_via_dscl_output_variations(self, shell_detector, dscl_output, expected):
            """Test dscl with various output formats"""
            with patch('sys.platform', 'darwin'), \
                 patch('os.getenv', return_value='user'), \
                 patch('subprocess.run') as mock_run, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_run.return_value = Mock(returncode=0, stdout=dscl_output)
                result = shell_detector.detect_current_shell()
                assert result == expected

        @pytest.mark.parametrize("env_var,value,expected", [
            ('ZSH_NAME', 'zsh', ShellType.ZSH),
            ('ZSH_VERSION', '5.8', ShellType.ZSH),
            ('BASH_VERSION', '5.0', ShellType.BASH),
        ])
        def test_detect_via_env_vars(self, shell_detector, env_var, value, expected):
            """Test detection via shell-specific environment variables"""
            with patch.dict('os.environ', {env_var: value}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError):
                result = shell_detector.detect_current_shell()
                assert result == expected


        @pytest.mark.skipif(sys.platform == "win32", reason="Not Windows")
        @pytest.mark.parametrize("process_name,expected", [
            ('zsh', ShellType.ZSH),
            ('bash', ShellType.BASH),
            ('fish', ShellType.FISH),
            ('sh', ShellType.SH),
            ('-zsh', ShellType.ZSH),
            ('-bash', ShellType.BASH),
            ('-fish', ShellType.FISH),
            ('-sh', ShellType.SH),
            ('unknown_shell', ShellType.UNKNOWN),
            (None, ShellType.UNKNOWN),
            (12345, ShellType.UNKNOWN),
            ('', ShellType.UNKNOWN),
        ])
        def test_detect_via_parent_process(self, shell_detector, process_name, expected):
            """Test detection via parent process for various shell names"""
            with patch('sys.platform', 'linux'), \
                 patch('psutil.Process') as mock_process, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_parent = Mock()
                mock_parent.name.return_value = process_name
                mock_process.return_value = mock_parent
                result = shell_detector.detect_current_shell()
                assert result == expected

        @pytest.mark.skipif(sys.platform != "win32", reason="Windows specific")
        def test_detect_via_parent_process_windows(self, shell_detector):
            """Test that parent process detection returns UNKNOWN on Windows"""
            with patch('sys.platform', 'win32'), \
                 patch.dict('os.environ', {}, clear=True):
                result = shell_detector.detect_current_shell()
                assert result == ShellType.UNKNOWN


        @pytest.mark.skipif(sys.platform == "win32", reason="Not Windows")
        @pytest.mark.parametrize("exception", [OSError, PermissionError, RuntimeError, ValueError, AttributeError])
        def test_detect_via_parent_process_different_exceptions(self, shell_detector, exception):
            """Test psutil.Process raising different exceptions"""
            with patch('sys.platform', 'linux'), \
                 patch('psutil.Process', side_effect=exception), \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('subprocess.run', side_effect=Exception), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                result = shell_detector.detect_current_shell()
                assert result == ShellType.UNKNOWN


        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        @pytest.mark.parametrize("version,expected", [
            ('10.14.0', ShellType.UNKNOWN),  # Mojave, before Catalina
            ('10.15.0', ShellType.ZSH),  # Catalina
            ('11.0.0', ShellType.ZSH),  # Big Sur
            ('12.0.0', ShellType.ZSH),  # Monterey
            ('13.0.0', ShellType.ZSH),  # Ventura
            ('14.0.0', ShellType.ZSH),  # Sonoma
            ('15.0.0', ShellType.ZSH),  # Sequoia
            ('20.0.0', ShellType.ZSH),  # Future version
        ])
        def test_detect_via_macos_default_zsh(self, shell_detector, version, expected):
            """Test macOS default detection for zsh with various versions"""
            with patch('sys.platform', 'darwin'), \
                 patch('subprocess.run') as mock_run, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_run.return_value = Mock(returncode=0, stdout=f'{version}\n')
                result = shell_detector.detect_current_shell()
                assert result == expected


        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        @pytest.mark.parametrize("exception", [
            subprocess.CalledProcessError(1, 'cmd'),
            subprocess.TimeoutExpired('cmd', 5),
        ])
        def test_detect_via_macos_default_exceptions(self, shell_detector, exception):
            """Test handling of exceptions in macOS default detection"""
            with patch('sys.platform', 'darwin'), \
                 patch('subprocess.run', side_effect=exception), \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                result = shell_detector.detect_current_shell()
                assert result == ShellType.UNKNOWN

        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        def test_detect_via_macos_default_value_error(self, shell_detector):
            """Test handling of ValueError in macOS default detection"""
            with patch('sys.platform', 'darwin'), \
                 patch('subprocess.run') as mock_run, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_run.return_value = Mock(returncode=0, stdout='invalid\n')
                result = shell_detector.detect_current_shell()
                assert result == ShellType.UNKNOWN

        # Version parsing edge cases for sw_vers
        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        @pytest.mark.parametrize("version_output,expected", [
            ('10\n', ShellType.UNKNOWN),  # Single component
            ('10.abc.0\n', ShellType.UNKNOWN),  # Non-numeric
            ('not.a.version.at.all\n', ShellType.UNKNOWN),
            ('10.15.beta\n', ShellType.UNKNOWN),  # ValueError on map(int, ['10','15','beta'])
            ('10..15.0\n', ShellType.UNKNOWN),
            ('10.15.\n', ShellType.UNKNOWN),  # ValueError on map(int, ['10','15',''])
            ('.10.15.0\n', ShellType.UNKNOWN),
            ('10.15.0.extra.components\n', ShellType.UNKNOWN),
            ('10.15.0\nextra\n', ShellType.ZSH),  # Parses first line '10.15.0', which is valid
            ('invalid.version\n', ShellType.UNKNOWN),
            ('10.15\n', ShellType.ZSH),  # Valid version
        ])
        def test_detect_via_sw_vers_malformed_versions(self, shell_detector, version_output, expected):
            """Test sw_vers with malformed version strings"""
            with patch('sys.platform', 'darwin'), \
                 patch('subprocess.run') as mock_run, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_run.return_value = Mock(returncode=0, stdout=version_output)
                result = shell_detector.detect_current_shell()
                assert result == expected

        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS specific")
        @pytest.mark.parametrize("sw_vers_output,expected", [
            ('', ShellType.UNKNOWN),
            ('not.a.version\n', ShellType.UNKNOWN),
            ('10.15\nextra\nlines\n', ShellType.ZSH),  # Should parse first line
        ])
        def test_detect_via_sw_vers_output_variations(self, shell_detector, sw_vers_output, expected):
            """Test sw_vers with various output formats"""
            with patch('sys.platform', 'darwin'), \
                 patch('subprocess.run') as mock_run, \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                mock_run.return_value = Mock(returncode=0, stdout=sw_vers_output)
                result = shell_detector.detect_current_shell()
                assert result == expected


        # Edge case tests for unusual environment variables
        @pytest.mark.parametrize("shell_env,expected", [
            ("/bin/zsh with spaces", ShellType.ZSH),  # Spaces in path
            ('"/bin/bash"', ShellType.BASH),  # Quoted path
            ("'/usr/bin/fish'", ShellType.FISH),  # Single quoted path
            ("./relative/zsh", ShellType.ZSH),  # Relative path
            ("../parent/bash", ShellType.BASH),  # Parent relative path
            ("/malformed/path/zsh/extra", ShellType.ZSH),  # Extra components
            ("/path/with/special!@#$%^&*()chars/bash", ShellType.BASH),  # Special chars
            ("zsh", ShellType.ZSH),  # Just shell name
            ("bash", ShellType.BASH),  # Just shell name
            ("fish", ShellType.FISH),  # Just shell name
            ("sh", ShellType.SH),  # Just shell name
            ("", ShellType.UNKNOWN),  # Empty string
            ("unknown_shell", ShellType.SH),  # Unknown shell falls back to sh detection
            ("/bin/unknown", ShellType.UNKNOWN),  # Unknown path
            ("   ", ShellType.UNKNOWN),  # Whitespace only
            ("\n\t", ShellType.UNKNOWN),  # Control chars
            ("C:\\Windows\\System32\\bash.exe", ShellType.BASH),  # Windows-style path (though unlikely on Unix)
        ])
        def test_detect_via_shell_env_edge_cases(self, shell_detector, shell_env, expected):
            """Test detection via SHELL environment variable with edge cases"""
            with patch.dict('os.environ', {'SHELL': shell_env}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch('subprocess.run', side_effect=Exception), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                result = shell_detector.detect_current_shell()
                assert result == expected

    class TestGetShellHintsFromConfigs:
        """Tests for shell detection via configuration file hints (.zshrc, .bashrc, .config/fish)"""

        @pytest.mark.parametrize("config_file,expected", [
            ('.zshrc', ShellType.ZSH),
            ('.bashrc', ShellType.BASH),
            ('.config/fish/config.fish', ShellType.FISH),
        ])
        def test_hints_from_configs(self, mock_home_dir, config_file, expected):
            """Test hints detection from configuration files"""
            detector = ShellDetector(home_dir=mock_home_dir)
            config_path = mock_home_dir / config_file
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.touch()
            result = detector._get_shell_hints_from_configs()
            assert result == expected

        def test_hints_no_configs(self, mock_home_dir):
            """Test when no config files exist"""
            detector = ShellDetector(home_dir=mock_home_dir)
            result = detector._get_shell_hints_from_configs()
            assert result is None

    class TestFindConfigFiles:
        """Tests for finding and returning shell configuration files for different shell types"""

        def test_find_config_files_zsh(self, mock_home_dir):
            """Test finding zsh config files"""
            detector = ShellDetector(home_dir=mock_home_dir)
            mock_home_dir.mkdir(parents=True, exist_ok=True)
            (mock_home_dir / '.zshrc').touch()
            (mock_home_dir / '.zshenv').touch()
            result = detector.find_config_files(ShellType.ZSH)
            expected = {
                '.zshrc': mock_home_dir / '.zshrc',
                '.zshenv': mock_home_dir / '.zshenv'
            }
            assert result == expected

        def test_find_config_files_no_shell_type(self, mock_home_dir):
            """Test finding config files without specifying shell type"""
            detector = ShellDetector(home_dir=mock_home_dir)
            mock_home_dir.mkdir(parents=True, exist_ok=True)
            with patch.object(detector, 'detect_current_shell', return_value=ShellType.BASH):
                (mock_home_dir / '.bashrc').touch()
                result = detector.find_config_files()
                expected = {'.bashrc': mock_home_dir / '.bashrc'}
                assert result == expected

        def test_find_config_files_unknown_shell(self, mock_home_dir):
            """Test finding config files for unknown shell"""
            detector = ShellDetector(home_dir=mock_home_dir)
            result = detector.find_config_files(ShellType.UNKNOWN)
            assert result == {}

        def test_find_config_files_nonexistent(self, mock_home_dir):
            """Test when config files don't exist"""
            detector = ShellDetector(home_dir=mock_home_dir)
            result = detector.find_config_files(ShellType.BASH)
            assert result == {}


        @pytest.mark.parametrize("platform,expected", [
            ('DARWIN', ShellType.UNKNOWN),  # Upper case, should not match darwin
            ('Darwin', ShellType.UNKNOWN),  # Mixed case, should not match darwin
            ('linux', ShellType.UNKNOWN),  # Lower case linux
            ('Linux', ShellType.UNKNOWN),  # Mixed case Linux
            ('win32', ShellType.UNKNOWN),  # Lower case win32
            ('Win32', ShellType.UNKNOWN),  # Mixed case Win32
        ])
        def test_detect_platform_case_variations(self, shell_detector, platform, expected):
            """Test platform detection with case variations"""
            with patch('sys.platform', platform), \
                 patch.dict('os.environ', {}, clear=True), \
                 patch('pwd.getpwuid', side_effect=KeyError), \
                 patch('psutil.Process', side_effect=ImportError), \
                 patch('subprocess.run', side_effect=Exception), \
                 patch.object(shell_detector, '_get_shell_hints_from_configs', return_value=None):
                result = shell_detector.detect_current_shell()
                assert result == expected