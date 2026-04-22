import asyncio
import sys
import httpx
from fastmcp import Client


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    mcp_servers = {
        "mcpServers": {
            "mcp_787967604072518": {
                "url": "http://192.168.2.137:8000/agent-toolkit/openapi/mcp/787967604072518"
            }
        }
    }

    server_name = "mcp_787967604072518"
    server_url = mcp_servers["mcpServers"][server_name]["url"]
    base_url = server_url.rstrip("/")
    parent_url = base_url.rsplit("/", 1)[0]

    attempts = [
        {"url": server_url},
        {"url": server_url, "transport": "sse"},
        {"url": f"{base_url}/sse", "transport": "sse"},
        {"url": f"{parent_url}/sse", "transport": "sse"},
    ]

    tools = None
    errors: list[str] = []
    for cfg in attempts:
        trial_config = {
            "mcpServers": {
                server_name: cfg,
            }
        }
        try:
            print(f"trial_config: {trial_config}")
            async with Client(trial_config) as client:
                tools = await client.list_tools()
            mcp_servers = trial_config
            break
        except httpx.HTTPStatusError as exc:
            errors.append(f"{cfg} -> HTTP {exc.response.status_code}")
            print(f"{cfg} -> HTTP {exc.response.status_code}")
        except Exception as exc:
            errors.append(f"{cfg} -> {type(exc).__name__}: {exc}")
            print(f"{cfg} -> {type(exc).__name__}: {exc}")

    if tools is None:
        print("所有候选地址都失败，请确认服务端真实 MCP 入口和 transport：")
        for err in errors:
            print(f"- {err}")
        return

    print(f"server: {server_name}")
    print(f"url: {mcp_servers['mcpServers'][server_name]['url']}")
    print(f"tools_count: {len(tools)}")
    for idx, tool in enumerate(tools, 1):
        tool_name = getattr(tool, "name", "<unknown>")
        tool_desc = getattr(tool, "description", "") or ""
        print(f"{idx}. {tool_name}")
        if tool_desc:
            print(f"   - {tool_desc}")


asyncio.run(main())
