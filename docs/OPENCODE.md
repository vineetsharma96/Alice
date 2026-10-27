# Local OpenCode agents and MCP

This repository includes project-local OpenCode configuration in
[`opencode.json`](../opencode.json) and `.opencode/agents/`.

## Agents

- `codex` is the default primary implementation agent.
- `codex-reviewer` is a read-only review subagent.
- `codex-explorer` is a read-only repository exploration subagent.

The agent files intentionally do not hard-code an OpenAI model ID. They inherit
the model selected for the current OpenCode session, so they remain usable with
the provider configured on the machine. To run them with an OpenAI Codex model,
select an available Codex model in OpenCode after the OpenAI provider is
authenticated. This avoids pinning a model name that may not be available in a
given account or provider catalog.

## MCP servers

### TinyFish (local proxy)

OpenCode connects to TinyFish through its loopback Streamable HTTP endpoint at
`http://127.0.0.1:3711/mcp`. TinyFish's local package is an HTTP proxy rather
than a stdio server, so it is configured as a remote MCP endpoint whose process
runs locally. The proxy reads `TINYFISH_API_KEY` from the environment and keeps
that key off the OpenCode config.

PowerShell:

```powershell
$env:TINYFISH_API_KEY = 'tf_replace_me'
& .\scripts\start-tinyfish-mcp.ps1
```

Linux/macOS shell:

```sh
export TINYFISH_API_KEY='tf_replace_me'
sh ./scripts/start-tinyfish-mcp.sh
```

Keep that process running while OpenCode uses TinyFish. The proxy should report
`http://127.0.0.1:3711` as its listening address. If you use another port, set
`PORT` before starting it and update the URL in `opencode.json` to match.

### Playwright

The Playwright MCP server is configured as a local stdio server and is started
by OpenCode with the pinned project dependency via `npm exec --offline --
playwright-mcp` when needed. It is intended for
browser/UI inspection and verification. Filesystem and Git MCP servers are not
duplicated because OpenCode already provides native workspace and shell tools
for those operations.

## Restart and check

OpenCode loads project configuration at startup. Quit and restart OpenCode
after changing `opencode.json` or an agent file, then check the configured
servers with:

```powershell
opencode agent list
opencode mcp list
```

TinyFish will show as unavailable until its local proxy is running. The
Playwright server may start when its catalog is first requested.
