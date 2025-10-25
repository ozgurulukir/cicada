#!/usr/bin/env python
"""
Demo script to show usage examples with ±2 context lines.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cicada.mcp_server import CicadaServer


async def demo():
    """Demo the usage examples feature."""
    # Create server with test index
    server = CicadaServer(config_path="config.yaml")

    # Override index to use test index
    import json
    with open("data/test_index.json", 'r') as f:
        server.index = json.load(f)

    print("Demo: Function usage examples with ±2 context lines\n")

    # Search for run_property_test which is likely to have call sites
    result = await server._search_function(
        "run_property_test/3",
        "markdown",
        include_usage_examples=True,
        max_examples=5
    )
    print(result[0].text)


if __name__ == "__main__":
    asyncio.run(demo())
