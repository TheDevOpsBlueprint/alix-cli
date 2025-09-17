# Testing Guide for alix

## Safe Testing Principles

### Test Alias Convention
We use a dedicated test alias that won't conflict with real aliases:
- **Name**: `alix-test-echo`
- **Command**: `echo 'alix test working!'`

### Testing Workflow
1. Always use the test alias name for testing
2. Create the test alias
3. Verify it works
4. Remove it immediately after testing
5. Never modify existing user aliases

### Example Test Pattern
```bash
# Add test alias
alix add -n "alix-test-echo" -c "echo 'alix test working!'"

# Test it works
alix-test-echo  # Should output: alix test working!

# Remove test alias
alix remove "alix-test-echo"