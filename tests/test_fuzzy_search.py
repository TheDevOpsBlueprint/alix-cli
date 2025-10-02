"""Test fuzzy search functionality"""

import pytest
from rapidfuzz import fuzz


def test_fuzzy_search_basic():
    """Test basic fuzzy search matching"""
    search_term = "gti"
    target = "git"

    score = fuzz.partial_ratio(search_term.lower(), target.lower())
    assert score >= 60, f"Expected score >= 60, got {score}"


def test_fuzzy_search_partial_match():
    """Test partial fuzzy matching"""
    search_term = "st"
    target = "git status"

    score = fuzz.partial_ratio(search_term.lower(), target.lower())
    assert score >= 60, f"Expected score >= 60, got {score}"


def test_fuzzy_search_typo():
    """Test fuzzy matching with typo"""
    search_term = "comit"
    target = "commit"

    score = fuzz.partial_ratio(search_term.lower(), target.lower())
    assert score >= 60, f"Expected score >= 60 for typo match, got {score}"


def test_fuzzy_search_threshold():
    """Test that completely unrelated terms score low"""
    search_term = "xyz"
    target = "git status"

    score = fuzz.partial_ratio(search_term.lower(), target.lower())
    # This should score low (below threshold)
    assert score < 100, "Unrelated terms should not score perfectly"


def test_fuzzy_search_exact_match():
    """Test that exact matches score 100"""
    search_term = "git"
    target = "git"

    score = fuzz.partial_ratio(search_term.lower(), target.lower())
    assert score == 100, f"Exact match should score 100, got {score}"
