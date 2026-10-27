$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($env:TINYFISH_API_KEY)) {
    throw 'Set TINYFISH_API_KEY before starting the TinyFish MCP proxy.'
}

& npm exec --offline -- tinyfish-mcp
