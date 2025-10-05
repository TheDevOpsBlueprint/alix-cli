# Testing Guide for alix

## Safe Testing Principles

### Test Alias Convention
We use a dedicated test alias that won't conflict with real aliases:
- Name: `alix-test-echo`
- Command: `echo 'alix test working!'`

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
```

## Tag Commands Test Plan

This section documents manual tests for tag management features.

Preconditions:
- Use the test alias name `alix-test-echo` throughout.
- When adding initially, include starting tags to validate tag operations.

Setup:
- Ensure a clean slate for this alias name. If it exists already, either remove it or add with `--force`.

1.1 alix add — Tags appear in list
- Command:
  - alix add -n "alix-test-echo" -c "echo 'alix test working!'" -d "Test alias for tag flows" -t "tag1,tag2,tag3" --force
- Validate:
  - alix list shows the alias with Tags column including tag1, tag2, tag3

1.2 alix tag add — Tags added
- Command:
  - alix tag add alix-test-echo newtag another
- Validate:
  - Console reports: Added 2 tag(s)
  - alix tag show newtag lists alias `alix-test-echo`
  - alix tag show another lists alias `alix-test-echo`

1.3 alix tag remove — Tags removed
- Command:
  - alix tag remove alix-test-echo newtag
- Validate:
  - Console reports: Removed 1 tag(s)
  - alix tag show newtag does not list `alix-test-echo`

1.4 alix tag rename — Tag renamed
- Dry-run:
  - alix tag rename tag1 tag1-renamed --dry-run
  - Validate: Lists aliases that would change (should include `alix-test-echo`)
- Apply:
  - alix tag rename tag1 tag1-renamed  # confirm when prompted
- Validate:
  - alix tag show tag1-renamed lists `alix-test-echo`
  - alix tag show tag1 shows no entries for `alix-test-echo`

1.5 alix tag delete — Tag deleted
- Command:
  - alix tag delete tag2  # confirm when prompted
- Validate:
  - alix tag show tag2 shows no entries for `alix-test-echo`

1.6 alix tag list — Tag table correct
- Command:
  - alix tag list
- Validate:
  - Table shows tag counts, and sample Aliases column includes `alix-test-echo` for the tags it still has

1.7 alix tag show — Aliases listed
- Command:
  - alix tag show tag3
- Validate:
  - Table lists `alix-test-echo` among entries

2.1 alix tag export — File contains correct aliases
- Command:
  - alix tag export tag1-renamed -f /tmp/alix_tag_tag1-renamed.json
- Validate:
  - Success message shows file path
  - cat /tmp/alix_tag_tag1-renamed.json contains field "tag": "tag1-renamed"
  - Aliases array contains entry with "name": "alix-test-echo"

2.2 alix tag export-multi — File contains correct aliases (ANY match)
- Command:
  - alix tag export-multi tag1-renamed tag3 -f /tmp/alix_tags_any.json
- Validate:
  - File exists and includes aliases that have any of the specified tags
  - Should include `alix-test-echo` (has tag1-renamed and tag3)

2.3 alix tag export-multi --match-all — File contains correct aliases (ALL match)
- Command:
  - alix tag export-multi tag1-renamed tag3 --match-all -f /tmp/alix_tags_all.json
- Validate:
  - File includes only aliases that have both tags
  - Should include `alix-test-echo`

2.4 alix tag import ... --tag — Only correct aliases imported
- Preparation (optional if importing into a clean environment):
  - If the alias exists, skip import or use a file containing multiple aliases with mixed tags
- Command:
  - alix tag import-tag /tmp/alix_tags_any.json --tag tag3
- Validate:
  - Console shows Imported <N> aliases and possibly Skipped <M> existing aliases
  - Only aliases that include tag3 are imported; filtered count is reported

3 alix tag stats — Stats output correct
- Command:
  - alix tag stats
- Validate:
  - Output shows total tags, total/untagged/tagged aliases, top tag counts, and common combinations tables

Cleanup
- Remove any temporary export files:
  - rm -f /tmp/alix_tag_tag1-renamed.json /tmp/alix_tags_any.json /tmp/alix_tags_all.json
- Remove tags created during tests as needed:
  - alix tag delete another
- Optional: Remove test alias (if supported by your build of alix):
  - alix remove "alix-test-echo"
