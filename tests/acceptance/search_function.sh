#!/bin/bash
# Usage: ./tests/acceptance/search_function.sh function_name [OPTIONS]
# Options:
#   -e, --examples       Include usage examples
#   -t, --tests          Only show calls from test files
#   -a, --all            Show everything: examples from both code and tests
#   -n, --limit N        Limit number of examples to show (default: 5)
#
# Short flags can be combined:
#   -te or -et           Examples in tests only
#   -tea or -ate         Same as --all
#
# Examples:
#   ./tests/acceptance/search_function.sh add_numbers/2
#   ./tests/acceptance/search_function.sh NumberFunctions.add_numbers/2 --examples
#   ./tests/acceptance/search_function.sh AB.Generators.create_input_generator -te -n 10
#   ./tests/acceptance/search_function.sh AB.Generators.create_input_generator --all --limit 20

# Default values
WITH_EXAMPLES="False"
MAX_EXAMPLES=5
TEST_ONLY="False"
FUNCTION=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            WITH_EXAMPLES="True"
            TEST_ONLY="False"  # --all means show both code and tests, so don't filter to tests only
            shift
            ;;
        -e|--examples)
            WITH_EXAMPLES="True"
            shift
            ;;
        -t|--tests)
            TEST_ONLY="True"
            shift
            ;;
        -n|--limit)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                MAX_EXAMPLES=$2
                shift
            else
                echo "Error: --limit requires a numeric argument"
                exit 1
            fi
            shift
            ;;
        -[aetn]*)
            # Handle combined short flags like -te, -et, -tea, etc.
            flags="${1#-}"  # Remove leading dash
            shift
            # Process each character in the flag
            for ((i=0; i<${#flags}; i++)); do
                flag="${flags:$i:1}"
                case $flag in
                    a)
                        WITH_EXAMPLES="True"
                        TEST_ONLY="False"
                        ;;
                    e)
                        WITH_EXAMPLES="True"
                        ;;
                    t)
                        TEST_ONLY="True"
                        ;;
                    n)
                        # -n in combined flags requires next argument to be a number
                        if [[ $i -eq $((${#flags}-1)) ]] && [[ $1 =~ ^[0-9]+$ ]]; then
                            MAX_EXAMPLES=$1
                            shift
                        else
                            echo "Error: -n requires a numeric argument"
                            exit 1
                        fi
                        ;;
                esac
            done
            ;;
        *)
            # First non-option argument is the function name
            if [ -z "$FUNCTION" ]; then
                FUNCTION="$1"
            fi
            shift
            ;;
    esac
done

# Set default function if not provided
FUNCTION="${FUNCTION:-add_numbers/2}"

python -c "import asyncio; from cicada.mcp_server import CicadaServer; print(asyncio.run(CicadaServer(config_path='tests/fixtures/.cicada/config.yaml')._search_function('$FUNCTION', output_format='markdown', include_usage_examples=$WITH_EXAMPLES, max_examples=$MAX_EXAMPLES, test_files_only=$TEST_ONLY))[0].text)"
