#!/bin/bash
# Usage: ./tests/acceptance/check_moduledoc.sh ModuleName
#
# Tests that moduledoc is displayed when searching for modules

MODULE="${1:-AB.Generators}"

python -c "import asyncio; from cicada.mcp_server import CicadaServer; print(asyncio.run(CicadaServer(config_path='tests/fixtures/.cicada/config.yaml')._search_module('$MODULE', 'markdown'))[0].text)"
