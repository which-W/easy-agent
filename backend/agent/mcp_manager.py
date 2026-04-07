"""MCP (Model Context Protocol) manager for connecting to MCP servers"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

from config import get_settings, PROJECT_ROOT

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages persistent connections to MCP servers and exposes their tools."""

    def __init__(self):
        self.settings = get_settings()
        self.config_path = PROJECT_ROOT / self.settings.MCP_CONFIG_PATH
        # server_name -> {"session": ClientSession, "tools": list[Tool]}
        self.servers: Dict[str, Any] = {}
        self.exit_stack = AsyncExitStack()
        self._connected = False

    # ──────────────────────────────────────────────────────────────────────────
    # Connection lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    async def connect_all(self):
        """Read mcp_servers.json and open persistent connections to all servers."""
        if not self.config_path.exists():
            logger.warning("MCP config not found: %s", self.config_path)
            return

        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        mcp_servers = config.get("mcpServers", {})

        if not mcp_servers:
            logger.info("No MCP servers configured")
            return

        for server_name, server_config in mcp_servers.items():
            try:
                await self._connect_server(server_name, server_config)
            except Exception as e:
                logger.error("Failed to connect to MCP server '%s': %s", server_name, e)

        self._connected = True
        logger.info(
            "MCP initialised: %d server(s), %d tool(s) total",
            len(self.servers),
            self.tool_count,
        )

    async def _connect_server(self, name: str, config: Dict[str, Any]):
        """Open a *persistent* stdio connection and register the server's tools.

        The connection context managers are entered via self.exit_stack so they
        remain open for the lifetime of the application.
        """
        params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env") or None,
        )

        # Enter both context managers into the long-lived exit_stack —
        # this keeps the connection open until disconnect_all() is called.
        read, write = await self.exit_stack.enter_async_context(stdio_client(params))
        session: ClientSession = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await session.initialize()

        result = await session.list_tools()
        tools = result.tools  # list[mcp.types.Tool]

        # ✅ Actually store the session and tools so the rest of the code can use them
        self.servers[name] = {
            "session": session,
            "tools": tools,
        }

        print(f"✅ [MCP {name}] 已连接，发现 {len(tools)} 个工具:")
        for t in tools:
            print(f"   🛠️  {t.name}: {t.description or '(no description)'}")

    async def disconnect_all(self):
        """Close all MCP connections gracefully."""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            logger.error("Error while disconnecting MCP servers: %s", e)
        finally:
            self.servers.clear()
            self._connected = False
            logger.info("Disconnected from all MCP servers")

    # ──────────────────────────────────────────────────────────────────────────
    # Tool invocation
    # ──────────────────────────────────────────────────────────────────────────

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a tool on a specific MCP server (async)."""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' is not connected")
        session: ClientSession = self.servers[server_name]["session"]
        return await session.call_tool(tool_name, arguments)

    # ──────────────────────────────────────────────────────────────────────────
    # Toolkit creation (for AgentScope)
    # ──────────────────────────────────────────────────────────────────────────

    def create_toolkit(self):
        """Return an agentscope Toolkit populated with all MCP tools."""
        from agentscope.tool import Toolkit

        toolkit = Toolkit()

        for server_name, server_info in self.servers.items():
            for tool in server_info["tools"]:
                self._register_mcp_tool(
                    toolkit,
                    server_name=server_name,
                    tool_name=tool.name,
                    description=tool.description or f"MCP tool: {tool.name}",
                )

        logger.info("Toolkit created with %d MCP tool(s)", self.tool_count)
        return toolkit

    def _register_mcp_tool(self, toolkit, server_name: str, tool_name: str, description: str):
        """Register one MCP tool as a sync wrapper function in the toolkit."""

        manager = self  # capture for closure

        def tool_func(**kwargs) -> str:
            """Synchronous wrapper — bridges the async MCP call into the running event loop."""
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Inside FastAPI's running event loop — use thread-safe future
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(
                        manager.call_tool(server_name, tool_name, kwargs),
                        loop,
                    )
                    result = future.result(timeout=120)
                else:
                    result = asyncio.run(
                        manager.call_tool(server_name, tool_name, kwargs)
                    )
            except Exception as e:
                logger.error("MCP tool '%s' execution error: %s", tool_name, e)
                return f"Error executing tool '{tool_name}': {e}"

            # Normalise MCP result to a plain string
            if hasattr(result, "content"):
                parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    elif hasattr(item, "data"):
                        parts.append(str(item.data))
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            return str(result)

        tool_func.__name__ = tool_name
        tool_func.__doc__ = description

        try:
            toolkit.register_tool_function(tool_func, description=description)
            logger.info("Registered MCP tool: %s (from %s)", tool_name, server_name)
        except Exception as e:
            logger.error("Failed to register MCP tool '%s': %s", tool_name, e)

    # ──────────────────────────────────────────────────────────────────────────
    # Introspection
    # ──────────────────────────────────────────────────────────────────────────

    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Return a list of dicts describing every available MCP tool."""
        info = []
        for server_name, server_info in self.servers.items():
            for tool in server_info["tools"]:
                info.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "server": server_name,
                    "schema": getattr(tool, "inputSchema", {}),
                })
        return info

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tool_count(self) -> int:
        return sum(len(info["tools"]) for info in self.servers.values())