# Fuzzy Search Feature

## Overview
The fuzzy search feature enables users to find aliases even with typos or partial matches. This makes searching more flexible and user-friendly.

## Usage

### Toggling Fuzzy Search
Press `f` key to toggle fuzzy search on/off. The status bar will show:
- `Fuzzy ON` (green) when enabled
- `Fuzzy OFF` (dimmed) when disabled

### How It Works

#### Normal Search (Fuzzy OFF)
- Performs exact substring matching
- Search term must be contained in alias name, command, or description
- Case-insensitive

**Example:**
- Search: `git` 
- Matches: `git status`, `git commit`, `myGitAlias`
- Doesn't match: `gti`, `got`, `commit`

#### Fuzzy Search (Fuzzy ON)
- Uses intelligent fuzzy matching algorithm (rapidfuzz)
- Handles typos and partial matches
- Scores each match and shows best results first
- Only shows results with score >= 60%

**Example:**
- Search: `gti`
- Matches: `git` (typo), `git status`, `git commit`
- Sorted by relevance score

- Search: `comit`
- Matches: `commit`, `git commit`, `svn commit`

### Key Benefits
1. **Typo Tolerance**: Find `git` even if you type `gti`
2. **Partial Matches**: Search `st` finds `git status`
3. **Smart Ranking**: Best matches appear first
4. **Fast & Efficient**: Uses optimized rapidfuzz library

### Keybindings
- `f` - Toggle fuzzy search on/off
- `/` - Focus search input
- `Esc` - Clear search

## Technical Details

### Algorithm
Uses the `rapidfuzz` library with `partial_ratio` scoring:
- Searches across name, command, and description fields
- Takes the highest score among all fields
- 60% threshold for including results
- Results sorted by score (descending)

### Performance
- Fast C++ implementation via rapidfuzz
- Handles large alias collections efficiently
- No noticeable lag even with 1000+ aliases

### Dependencies
- `rapidfuzz>=3.0.0` - Fast fuzzy string matching

## Examples

### Example 1: Typo Correction
```
Aliases: git, svn, docker
Search: "gti" (Fuzzy ON)
Results: git (score: 100)
```

### Example 2: Partial Match
```
Aliases: git status, git commit, ls -la
Search: "st" (Fuzzy ON)
Results: git status (score: 100), ls -la (score: 67)
```

### Example 3: Command Search
```
Aliases: 
  - gs: git status
  - gc: git commit
  - gp: git push
Search: "commit" (Fuzzy ON)
Results: gc (matched in command)
```

## Testing
Run the fuzzy search tests:
```bash
python -m pytest tests/test_fuzzy_search.py -v
```

Tests cover:
- Basic fuzzy matching
- Partial matches
- Typo handling
- Threshold filtering
- Exact match scoring
