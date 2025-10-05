import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import ANY

import pytest

from alix.models import Alias


@pytest.fixture
def alias() -> Alias:
    return Alias(
        name="alix-test-echo",
        command="alix test working!",
        description="alix test shortcut",
        tags=["a", "b"],
        shell="zsh",
        created_at=datetime(2025, 10, 24, 16, 34, 21, 653023),
        last_used=None,
        usage_history=[],
        group=None,
    )


@pytest.fixture
def alias_min() -> Alias:
    return Alias(
        name="alix-test-echo",
        command="alix test working!",
        description="alix test shortcut",
        created_at=datetime(2025, 10, 24, 16, 34, 21, 653023),
    )


@pytest.fixture
def alias_list(alias, alias_min) -> List[Alias]:
    return [alias, alias_min]


@pytest.fixture
def porter_data() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "exported_at": ANY,
        "count": 2,
        "aliases": [
            {
                "name": "alix-test-echo",
                "command": "alix test working!",
                "description": "alix test shortcut",
                "created_at": "2025-10-24T16:34:21.653023",
                "shell": "zsh",
                "tags": ["a", "b"],
                "used_count": 0,
                "last_used": None,
                "usage_history": [],
                "group": None,
            },
            {
                "name": "alix-test-echo",
                "command": "alix test working!",
                "description": "alix test shortcut",
                "created_at": "2025-10-24T16:34:21.653023",
                "shell": None,
                "tags": [],
                "used_count": 0,
                "last_used": None,
                "usage_history": [],
                "group": None,
            },
        ],
    }


@pytest.fixture
def storage_file_raw_data() -> str:
    return """
    {
        "alix-test-echo": {
            "name": "alix-test-echo",
            "command": "alix test working!",
            "description": "alix test shortcut",
            "tags": ["a", "b"],
            "created_at": "2025-10-24T16:34:21.653023",
            "used_count": 0,
            "shell": "zsh",
            "last_used": null,
            "usage_history": [],
            "group": null
        }
    }
    """


@pytest.fixture
def storage_file_data(storage_file_raw_data) -> Dict[str, Any]:
    return json.loads(storage_file_raw_data)


@pytest.fixture
def shell_file_data() -> str:
    return """
    alias alix-test-echo='alix test working!'
    """
