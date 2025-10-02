#!/usr/bin/env python3
"""Quick test script to verify parameter functionality"""

from alix.parameters import ParameterParser
from alix.models import Alias
from alix.shell_integrator import ShellIntegrator
from alix.shell_detector import ShellType

def test_parameter_parsing():
    print("Testing Parameter Parsing...")
    
    # Test 1: Extract parameters
    command = "cp $1 $2"
    params = ParameterParser.extract_parameters(command)
    print(f"✓ Extracted parameters from '{command}': {params}")
    assert params == ["$1", "$2"]
    
    # Test 2: Validate parameters
    valid, error = ParameterParser.validate_parameters(command)
    print(f"✓ Validation result: valid={valid}, error={error}")
    assert valid is True
    
    # Test 3: Invalid parameters (gap)
    invalid_command = "echo $1 $3"
    valid, error = ParameterParser.validate_parameters(invalid_command)
    print(f"✓ Invalid command detected: '{invalid_command}' - error: {error}")
    assert valid is False
    
    # Test 4: Usage example generation
    usage = ParameterParser.generate_usage_example("copy", "cp $1 $2", {"$1": "source", "$2": "dest"})
    print(f"✓ Generated usage example: {usage}")
    assert usage == "copy <source> <dest>"
    
    # Test 5: Auto-detect descriptions
    descriptions = ParameterParser.auto_detect_parameter_descriptions("git commit -m '$1'")
    print(f"✓ Auto-detected descriptions for git commit: {descriptions}")
    assert descriptions.get("$1") == "message"
    
    print("\n✅ All parameter parsing tests passed!\n")

def test_alias_model():
    print("Testing Alias Model...")
    
    # Test 1: Alias with parameters
    alias = Alias(
        name="deploy",
        command="ssh $1 && cd /var/www && git pull",
        description="Deploy to server",
        parameters={"$1": "server"}
    )
    
    assert alias.has_parameters() is True
    print(f"✓ Alias has parameters: {alias.has_parameters()}")
    
    assert alias.get_parameter_count() == 1
    print(f"✓ Parameter count: {alias.get_parameter_count()}")
    
    usage = alias.get_usage_example()
    print(f"✓ Usage example: {usage}")
    assert usage == "deploy <server>"
    
    # Test 2: Alias without parameters
    simple_alias = Alias(name="ll", command="ls -la")
    assert simple_alias.has_parameters() is False
    print(f"✓ Simple alias has no parameters: {simple_alias.has_parameters()}")
    
    # Test 3: Serialization
    data = alias.to_dict()
    assert "parameters" in data
    print(f"✓ Parameters included in serialization: {data['parameters']}")
    
    # Test 4: Deserialization
    restored = Alias.from_dict(data)
    assert restored.parameters == {"$1": "server"}
    print(f"✓ Parameters restored from dict: {restored.parameters}")
    
    # Test 5: Backward compatibility (old aliases without parameters)
    old_data = {
        "name": "oldtest",
        "command": "echo test",
        "tags": [],
        "created_at": "2024-01-01T00:00:00",
        "used_count": 0,
        "shell": None,
        "last_used": None,
        "usage_history": [],
        "group": None
    }
    old_alias = Alias.from_dict(old_data)
    assert old_alias.parameters == {}
    print(f"✓ Backward compatibility: old alias has empty parameters dict")
    
    print("\n✅ All alias model tests passed!\n")

def test_shell_function_generation():
    print("Testing Shell Function Generation...")
    
    integrator = ShellIntegrator()
    
    # Test 1: Bash function generation
    alias = Alias(name="backup", command="tar -czf backup_$1.tar.gz $1")
    function_code = integrator._generate_function(alias, ShellType.BASH)
    print(f"✓ Generated bash function:\n{function_code}\n")
    assert "backup()" in function_code
    assert "tar -czf" in function_code
    
    # Test 2: Fish function generation
    function_code = integrator._generate_function(alias, ShellType.FISH)
    print(f"✓ Generated fish function:\n{function_code}\n")
    assert "function backup" in function_code
    assert "end" in function_code
    
    # Test 3: Simple alias (no parameters)
    simple_alias = Alias(name="ll", command="ls -la")
    assert not ParameterParser.has_parameters(simple_alias.command)
    print(f"✓ Simple alias correctly identified as non-parameterized")
    
    print("\n✅ All shell function generation tests passed!\n")

def test_edge_cases():
    print("Testing Edge Cases...")
    
    # Test 1: Multiple parameter usage
    command = "echo $1 $1 $2 $1"
    params = ParameterParser.extract_parameters(command)
    assert params == ["$1", "$2"]
    print(f"✓ Duplicate parameters handled: {params}")
    
    # Test 2: Special parameters
    command = "process $@ and $1"
    params = ParameterParser.extract_parameters(command)
    assert "$1" in params
    assert "$@" in params
    print(f"✓ Special parameters detected: {params}")
    
    # Test 3: Parameters in quotes
    command = "git commit -m '$1 - $2'"
    params = ParameterParser.extract_parameters(command)
    assert len(params) == 2
    print(f"✓ Parameters in quotes detected: {params}")
    
    # Test 4: Complex command with multiple parameters
    command = "docker run -d --name $1 -p $2:$3 -e ENV=$4 $5"
    params = ParameterParser.extract_parameters(command)
    assert len(params) == 5
    print(f"✓ Complex command with 5 parameters: {params}")
    
    valid, error = ParameterParser.validate_parameters(command)
    assert valid is True
    print(f"✓ Complex command validated successfully")
    
    print("\n✅ All edge case tests passed!\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Alias Parameter Implementation")
    print("=" * 60 + "\n")
    
    try:
        test_parameter_parsing()
        test_alias_model()
        test_shell_function_generation()
        test_edge_cases()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
