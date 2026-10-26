#!/usr/bin/env sh
set -eu

: "${TINYFISH_API_KEY:?Set TINYFISH_API_KEY before starting the TinyFish MCP proxy.}"
exec npm exec --offline -- tinyfish-mcp
