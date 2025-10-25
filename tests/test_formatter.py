#!/usr/bin/env python
"""
Tests for the formatter module, including call site consolidation.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.formatter import ModuleFormatter


def test_group_call_sites_by_caller_single_caller():
    """Test that multiple call sites from the same caller are grouped together."""
    call_sites = [
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 261,
            "code_line": "    GenServer.cast(pid, :update_presence)"
        },
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 312,
            "code_line": "    GenServer.cast(pid, :update_presence)"
        },
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 358,
            "code_line": "    GenServer.cast(pid, :update_presence)"
        },
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 387,
            "code_line": "    GenServer.cast(pid, :update_presence)"
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have exactly 1 grouped entry
    assert len(grouped) == 1, f"Expected 1 grouped entry, got {len(grouped)}"

    # Should have all 4 lines
    assert grouped[0]['lines'] == [261, 312, 358, 387], \
        f"Expected lines [261, 312, 358, 387], got {grouped[0]['lines']}"

    # Should have all 4 code lines
    assert len(grouped[0]['code_lines']) == 4, \
        f"Expected 4 code lines, got {len(grouped[0]['code_lines'])}"

    # Verify the caller info is preserved
    assert grouped[0]['calling_module'] == "ThenvoiComWeb.Api.V1.UserRoomsChannel"
    assert grouped[0]['calling_function']['name'] == "handle_info"
    assert grouped[0]['calling_function']['arity'] == 2


def test_group_call_sites_by_caller_multiple_callers():
    """Test that call sites from different callers are kept separate."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 10,
        },
        {
            "calling_module": "MyApp.ModuleB",
            "calling_function": {"name": "func2", "arity": 2},
            "file": "lib/my_app/module_b.ex",
            "line": 20,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 15,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have 2 grouped entries (ModuleA.func1/1 and ModuleB.func2/2)
    assert len(grouped) == 2, f"Expected 2 grouped entries, got {len(grouped)}"

    # Find the ModuleA group
    module_a_group = [g for g in grouped if g['calling_module'] == "MyApp.ModuleA"][0]
    assert module_a_group['lines'] == [10, 15], \
        f"Expected lines [10, 15] for ModuleA, got {module_a_group['lines']}"

    # Find the ModuleB group
    module_b_group = [g for g in grouped if g['calling_module'] == "MyApp.ModuleB"][0]
    assert module_b_group['lines'] == [20], \
        f"Expected lines [20] for ModuleB, got {module_b_group['lines']}"


def test_group_call_sites_by_caller_same_module_different_functions():
    """Test that call sites from the same module but different functions are kept separate."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 10,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func2", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 20,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 15,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have 2 grouped entries (func1/1 and func2/1)
    assert len(grouped) == 2, f"Expected 2 grouped entries, got {len(grouped)}"

    # Find the func1 group
    func1_group = [g for g in grouped if g['calling_function']['name'] == "func1"][0]
    assert func1_group['lines'] == [10, 15], \
        f"Expected lines [10, 15] for func1, got {func1_group['lines']}"

    # Find the func2 group
    func2_group = [g for g in grouped if g['calling_function']['name'] == "func2"][0]
    assert func2_group['lines'] == [20], \
        f"Expected lines [20] for func2, got {func2_group['lines']}"


def test_group_call_sites_by_caller_no_calling_function():
    """Test that call sites without calling_function are grouped by module only."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "file": "lib/my_app/module_a.ex",
            "line": 10,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "file": "lib/my_app/module_a.ex",
            "line": 20,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have 1 grouped entry (same module, no function info)
    assert len(grouped) == 1, f"Expected 1 grouped entry, got {len(grouped)}"

    # Should have both lines
    assert grouped[0]['lines'] == [10, 20], \
        f"Expected lines [10, 20], got {grouped[0]['lines']}"

    # calling_function should be None
    assert grouped[0]['calling_function'] is None


def test_group_call_sites_lines_are_sorted():
    """Test that line numbers in grouped results are sorted."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 100,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 50,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 75,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Lines should be sorted
    assert grouped[0]['lines'] == [50, 75, 100], \
        f"Expected sorted lines [50, 75, 100], got {grouped[0]['lines']}"


def test_format_function_results_markdown_with_consolidated_call_sites():
    """Test that the markdown formatter uses consolidated call sites."""
    results = [
        {
            "module": "MyApp.TargetModule",
            "function": {
                "name": "target_function",
                "arity": 2,
                "type": "def",
                "line": 42,
                "args": ["arg1", "arg2"],
            },
            "file": "lib/my_app/target_module.ex",
            "call_sites": [
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "handle_info", "arity": 2},
                    "file": "lib/my_app/caller.ex",
                    "line": 10,
                },
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "handle_info", "arity": 2},
                    "file": "lib/my_app/caller.ex",
                    "line": 20,
                },
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "handle_info", "arity": 2},
                    "file": "lib/my_app/caller.ex",
                    "line": 30,
                },
            ],
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "target_function", results
    )

    # Should have a single consolidated line for the caller
    assert "`MyApp.Caller.handle_info/2` at `lib/my_app/caller.ex`:10, :20, :30" in markdown, \
        "Expected consolidated call sites in markdown output"

    # Should NOT have multiple separate lines for the same caller
    lines = markdown.split("\n")
    caller_lines = [line for line in lines if "MyApp.Caller.handle_info/2" in line]
    assert len(caller_lines) == 1, \
        f"Expected 1 line for caller, got {len(caller_lines)}: {caller_lines}"


def test_format_function_results_markdown_with_code_lines():
    """Test that consolidated call sites properly display code examples."""
    results = [
        {
            "module": "MyApp.TargetModule",
            "function": {
                "name": "target_function",
                "arity": 1,
                "type": "def",
                "line": 42,
                "args": ["arg1"],
            },
            "file": "lib/my_app/target_module.ex",
            "call_sites": [
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "process", "arity": 1},
                    "file": "lib/my_app/caller.ex",
                    "line": 10,
                    "code_line": "    TargetModule.target_function(data)",
                },
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "process", "arity": 1},
                    "file": "lib/my_app/caller.ex",
                    "line": 20,
                    "code_line": "    TargetModule.target_function(other_data)",
                },
            ],
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "target_function", results
    )

    # Should have consolidated header
    assert "`MyApp.Caller.process/1` at `lib/my_app/caller.ex`:10, :20" in markdown, \
        "Expected consolidated call sites header in markdown output"

    # Should have both code examples
    assert ":10" in markdown and ":20" in markdown, \
        "Expected both line numbers in output"
    assert "TargetModule.target_function(data)" in markdown, \
        "Expected first code example"
    assert "TargetModule.target_function(other_data)" in markdown, \
        "Expected second code example"
