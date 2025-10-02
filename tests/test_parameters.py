"""Tests for parameter parsing and validation"""

import pytest
from alix.parameters import ParameterParser
from alix.models import Alias


class TestParameterParsing:
    """Test parameter extraction and parsing"""

    def test_extract_single_parameter(self):
        """Test extracting a single parameter"""
        command = "echo $1"
        params = ParameterParser.extract_parameters(command)
        assert params == ['$1']

    def test_extract_multiple_parameters(self):
        """Test extracting multiple parameters"""
        command = "cp $1 $2"
        params = ParameterParser.extract_parameters(command)
        assert params == ['$1', '$2']

    def test_extract_non_sequential_parameters(self):
        """Test extracting non-sequential parameters"""
        command = "echo $1 $3 $2"
        params = ParameterParser.extract_parameters(command)
        # Should be sorted by number
        assert params == ['$1', '$2', '$3']

    def test_extract_special_parameters(self):
        """Test extracting special parameters like $@ and $*"""
        command = "echo $@"
        params = ParameterParser.extract_parameters(command)
        assert '$@' in params

        command = "echo $*"
        params = ParameterParser.extract_parameters(command)
        assert '$*' in params

    def test_extract_mixed_parameters(self):
        """Test extracting a mix of positional and special parameters"""
        command = "mycommand $1 $2 $@"
        params = ParameterParser.extract_parameters(command)
        assert '$1' in params
        assert '$2' in params
        assert '$@' in params

    def test_no_parameters(self):
        """Test command with no parameters"""
        command = "echo hello world"
        params = ParameterParser.extract_parameters(command)
        assert params == []

    def test_get_max_parameter_index(self):
        """Test getting maximum parameter index"""
        assert ParameterParser.get_max_parameter_index("echo $1") == 1
        assert ParameterParser.get_max_parameter_index("cp $1 $2 $3") == 3
        assert ParameterParser.get_max_parameter_index("echo hello") == 0

    def test_has_parameters(self):
        """Test checking if command has parameters"""
        assert ParameterParser.has_parameters("echo $1") is True
        assert ParameterParser.has_parameters("cp $1 $2") is True
        assert ParameterParser.has_parameters("echo $@") is True
        assert ParameterParser.has_parameters("echo hello") is False


class TestParameterValidation:
    """Test parameter validation"""

    def test_valid_sequential_parameters(self):
        """Test validation of sequential parameters"""
        command = "cp $1 $2"
        is_valid, error = ParameterParser.validate_parameters(command)
        assert is_valid is True
        assert error is None

    def test_parameters_start_at_one(self):
        """Test that parameters must start at $1"""
        command = "echo $2"
        is_valid, error = ParameterParser.validate_parameters(command)
        assert is_valid is False
        assert "should start at $1" in error

    def test_no_gaps_in_parameters(self):
        """Test that parameters cannot have gaps"""
        command = "mycommand $1 $3"
        is_valid, error = ParameterParser.validate_parameters(command)
        assert is_valid is False
        assert "Missing parameter $2" in error

    def test_valid_command_without_parameters(self):
        """Test validation of command without parameters"""
        command = "echo hello world"
        is_valid, error = ParameterParser.validate_parameters(command)
        assert is_valid is True
        assert error is None

    def test_valid_with_special_parameters(self):
        """Test validation with special parameters"""
        command = "mycommand $@"
        is_valid, error = ParameterParser.validate_parameters(command)
        assert is_valid is True


class TestUsageExampleGeneration:
    """Test usage example generation"""

    def test_simple_command_usage(self):
        """Test usage example for simple command"""
        usage = ParameterParser.generate_usage_example("myalias", "echo hello", {})
        assert usage == "myalias"

    def test_single_parameter_usage(self):
        """Test usage example with single parameter"""
        usage = ParameterParser.generate_usage_example("backup", "cp $1 $1.bak", {})
        assert usage == "backup <arg1>"

    def test_multiple_parameters_usage(self):
        """Test usage example with multiple parameters"""
        usage = ParameterParser.generate_usage_example("copy", "cp $1 $2", {})
        assert usage == "copy <arg1> <arg2>"

    def test_usage_with_descriptions(self):
        """Test usage example with parameter descriptions"""
        descriptions = {"$1": "source", "$2": "destination"}
        usage = ParameterParser.generate_usage_example("copy", "cp $1 $2", descriptions)
        assert usage == "copy <source> <destination>"

    def test_usage_with_special_parameters(self):
        """Test usage example with special parameters"""
        usage = ParameterParser.generate_usage_example("runall", "mycommand $@", {})
        assert "all arguments" in usage


class TestAutoDetectDescriptions:
    """Test auto-detection of parameter descriptions"""

    def test_detect_cp_command(self):
        """Test detecting cp command parameters"""
        command = "cp $1 $2"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'source'
        assert descriptions.get('$2') == 'destination'

    def test_detect_mv_command(self):
        """Test detecting mv command parameters"""
        command = "mv $1 $2"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'source'
        assert descriptions.get('$2') == 'destination'

    def test_detect_git_commit(self):
        """Test detecting git commit parameters"""
        command = "git commit -m $1"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'message'

    def test_detect_ssh_command(self):
        """Test detecting ssh command parameters"""
        command = "ssh $1"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'host'

    def test_detect_curl_command(self):
        """Test detecting curl command parameters"""
        command = "curl $1"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'url'

    def test_detect_echo_command(self):
        """Test detecting echo command parameters"""
        command = "echo $1"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'message'

    def test_detect_grep_command(self):
        """Test detecting grep command parameters"""
        command = "grep $1 $2"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        assert descriptions.get('$1') == 'pattern'
        assert descriptions.get('$2') == 'file'

    def test_no_detection_for_unknown_command(self):
        """Test no description for unknown command"""
        command = "unknowncommand $1 $2"
        descriptions = ParameterParser.auto_detect_parameter_descriptions(command)
        # Should return empty dict for unknown patterns
        assert len(descriptions) == 0


class TestAliasModelIntegration:
    """Test integration with Alias model"""

    def test_alias_has_parameters(self):
        """Test Alias.has_parameters() method"""
        alias_with_params = Alias(name="test", command="echo $1")
        assert alias_with_params.has_parameters() is True

        alias_without_params = Alias(name="test", command="echo hello")
        assert alias_without_params.has_parameters() is False

    def test_alias_get_parameter_count(self):
        """Test Alias.get_parameter_count() method"""
        alias = Alias(name="test", command="cp $1 $2 $3")
        assert alias.get_parameter_count() == 3

        alias_no_params = Alias(name="test", command="echo hello")
        assert alias_no_params.get_parameter_count() == 0

    def test_alias_get_usage_example(self):
        """Test Alias.get_usage_example() method"""
        alias = Alias(name="backup", command="cp $1 $1.bak")
        usage = alias.get_usage_example()
        assert usage == "backup <arg1>"

        # With parameter descriptions
        alias_with_desc = Alias(
            name="copy",
            command="cp $1 $2",
            parameters={"$1": "source", "$2": "destination"}
        )
        usage = alias_with_desc.get_usage_example()
        assert usage == "copy <source> <destination>"

    def test_alias_parameters_stored_in_dict(self):
        """Test that alias parameters are properly stored"""
        params = {"$1": "file", "$2": "output"}
        alias = Alias(name="test", command="process $1 $2", parameters=params)
        
        # Convert to dict and back
        data = alias.to_dict()
        assert data['parameters'] == params
        
        restored = Alias.from_dict(data)
        assert restored.parameters == params

    def test_alias_backward_compatibility(self):
        """Test backward compatibility for aliases without parameters field"""
        # Simulate old alias data without parameters field
        old_data = {
            "name": "test",
            "command": "echo hello",
            "description": None,
            "tags": [],
            "created_at": "2025-01-01T00:00:00",
            "used_count": 0,
            "shell": None,
            "last_used": None,
            "usage_history": [],
            "group": None
        }
        
        # Should not raise error and should have empty parameters dict
        alias = Alias.from_dict(old_data)
        assert alias.parameters == {}
