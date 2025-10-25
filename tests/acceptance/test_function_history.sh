#!/bin/bash
# Usage: ./tests/acceptance/test_function_history.sh [file_path] [function_name] [OPTIONS]
# Options:
#   -f, --function NAME      Function name to track (default: get_pr_info)
#   -e, --evolution          Include evolution metadata
#   -n, --limit N            Maximum commits to show (default: 5)
#   -l, --line-mode          Use line-based tracking instead of function tracking
#   --start LINE             Starting line for line-based mode
#   --end LINE               Ending line for line-based mode
#
# Examples:
#   # Track function across file (even as it moves)
#   ./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info
#
#   # With evolution metadata
#   ./tests/acceptance/test_function_history.sh cicada/git_helper.py get_pr_info --evolution
#
#   # Line-based tracking
#   ./tests/acceptance/test_function_history.sh cicada/git_helper.py --line-mode --start 40 --end 80
#
#   # Limit commits
#   ./tests/acceptance/test_function_history.sh README.md --line-mode --start 1 --end 50 -n 3

# Default values
FILE_PATH="${1:-cicada/git_helper.py}"
FUNCTION_NAME="get_pr_info"
WITH_EVOLUTION="False"
MAX_COMMITS=5
LINE_MODE="False"
START_LINE=""
END_LINE=""

# Shift first argument (file_path)
shift 2>/dev/null || true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--function)
            FUNCTION_NAME="$2"
            shift 2
            ;;
        -e|--evolution)
            WITH_EVOLUTION="True"
            shift
            ;;
        -n|--limit)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                MAX_COMMITS=$2
                shift 2
            else
                echo "Error: --limit requires a numeric argument"
                exit 1
            fi
            ;;
        -l|--line-mode)
            LINE_MODE="True"
            shift
            ;;
        --start)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                START_LINE=$2
                shift 2
            else
                echo "Error: --start requires a numeric argument"
                exit 1
            fi
            ;;
        --end)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                END_LINE=$2
                shift 2
            else
                echo "Error: --end requires a numeric argument"
                exit 1
            fi
            ;;
        *)
            # Treat non-option as function name
            FUNCTION_NAME="$1"
            shift
            ;;
    esac
done

# Determine config path - use test fixtures if available, otherwise use current directory
if [[ -f "tests/fixtures/.cicada/config.yaml" ]]; then
    CONFIG_PATH="tests/fixtures/.cicada/config.yaml"
else
    CONFIG_PATH=".cicada/config.yaml"
fi

# Build Python command based on mode
if [[ "$LINE_MODE" == "True" ]]; then
    # Line-based tracking
    if [[ -z "$START_LINE" || -z "$END_LINE" ]]; then
        echo "Error: Line mode requires --start and --end parameters"
        exit 1
    fi

    python -c "import asyncio; from cicada.mcp_server import CicadaServer; print(asyncio.run(CicadaServer(config_path='$CONFIG_PATH')._get_file_history('$FILE_PATH', start_line=$START_LINE, end_line=$END_LINE, show_evolution=$WITH_EVOLUTION, max_commits=$MAX_COMMITS))[0].text)"
else
    # Function-based tracking
    if [[ -n "$START_LINE" && -n "$END_LINE" ]]; then
        # Function tracking with fallback line numbers
        python -c "import asyncio; from cicada.mcp_server import CicadaServer; print(asyncio.run(CicadaServer(config_path='$CONFIG_PATH')._get_file_history('$FILE_PATH', function_name='$FUNCTION_NAME', start_line=$START_LINE, end_line=$END_LINE, show_evolution=$WITH_EVOLUTION, max_commits=$MAX_COMMITS))[0].text)"
    else
        # Function tracking only
        python -c "import asyncio; from cicada.mcp_server import CicadaServer; print(asyncio.run(CicadaServer(config_path='$CONFIG_PATH')._get_file_history('$FILE_PATH', function_name='$FUNCTION_NAME', show_evolution=$WITH_EVOLUTION, max_commits=$MAX_COMMITS))[0].text)"
    fi
fi
