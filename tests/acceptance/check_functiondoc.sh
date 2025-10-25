#!/bin/bash
# Usage: ./tests/acceptance/check_functiondoc.sh function_name
#
# Tests that:
# 1. Function @doc is displayed
# 2. Examples are extracted from @doc and shown separately

FUNCTION="${1:-resolve_all_types}"

python -c "import asyncio; from cicada.mcp_server import CicadaServer; print(asyncio.run(CicadaServer(config_path='tests/fixtures/.cicada/config.yaml')._search_function('$FUNCTION', output_format='markdown'))[0].text)"
