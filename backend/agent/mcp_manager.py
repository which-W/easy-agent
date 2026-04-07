"""MCP (Model Context Protocol) manager for connecting to MCP servers"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from config import get_settings, PROJECT_ROOT

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages connections to MCP servers and bridges their tools to agentscope Toolkit"""

    def __init__(self):
        self.settings = get_settings()
        self.config_path = PROJECT_ROOT / self.settings.MCP_CONFIG_PATH
        self.servers: Dict[str, Any] = {}  # server_name -> {session, tools, ...}
        self.exit_stack = AsyncExitStack()
        self._connected = False

    async def connect_all(self):
        """Read mcp_servers.json and connect to all configured servers via stdio"""
        if not self.config_path.exists():
            logger.warning(f"MCP config not found: {self.config_path}")
            return

        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        mcp_servers = config.get("mcpServers", {})

        if not mcp_servers:
            logger.info("No MCP servers configured")
            return

        for server_name, server_config in mcp_servers.items():
            try:
                await self._connect_server(server_name, server_config)
                logger.info(f"Connected to MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{server_name}': {e}")

        self._connected = True

    async def _connect_server(self, name: str, config: dict):
        """Connect to a single MCP server via stdio transport"""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        command = config.get("command", "")
        args = config.get("args", [])
        env = config.get("env", None)

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        # Use exit stack to manage the lifecycle
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport

        session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await session.initialize()

        # Discover tools
        tools_result = await session.list_tools()
        tools = tools_result.tools if hasattr(tools_result, 'tools') else []

        self.servers[name] = {
            "session": session,
            "tools": tools,
            "config": config
        }

        logger.info(f"MCP server '{name}' provides {len(tools)} tools")

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a tool on a specific MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' not connected")

        session = self.servers[server_name]["session"]
        result = await session.call_tool(tool_name, arguments)
        return result

    def create_toolkit(self):
        """Create an agentscope Toolkit with all MCP tools registered as wrapper functions"""
        from agentscope.tool import Toolkit

        toolkit = Toolkit()

        for server_name, server_info in self.servers.items():
            tools = server_info["tools"]

            for tool in tools:
                tool_name = tool.name
                tool_description = tool.description or f"MCP tool: {tool_name}"
                tool_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else {}

                # Create a wrapper function for this MCP tool
                # Need to capture server_name and tool_name in closure
                self._register_mcp_tool(toolkit, server_name, tool_name, tool_description, tool_schema)

        return toolkit

    def _register_mcp_tool(self, toolkit, server_name: str, tool_name: str, description: str, schema: dict):
        """Register a single MCP tool as a wrapper function in the toolkit"""

        # Build a dynamic function that calls the MCP tool
        # The function needs to accept **kwargs and bridge async to sync

        def make_tool_func(sname, tname, desc):
            def tool_func(**kwargs) -> str:
                """动态生成的 MCP 工具包装函数"""
                try:
                    # Bridge async call to sync
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an async context, create a task
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self.call_tool(sname, tname, kwargs)
                            )
                            result = future.result(timeout=120)
                    else:
                        result = asyncio.run(self.call_tool(sname, tname, kwargs))

                    # Process result
                    if hasattr(result, 'content'):
                        contents = result.content
                        text_parts = []
                        for content in contents:
                            if hasattr(content, 'text'):
                                text_parts.append(content.text)
                            elif hasattr(content, 'data'):
                                text_parts.append(str(content.data))
                            else:
                                text_parts.append(str(content))
                        return "\n".join(text_parts)
                    return str(result)
                except Exception as e:
                    logger.error(f"MCP tool '{tname}' execution error: {e}")
                    return f"Error executing tool '{tname}': {str(e)}"

            tool_func.__name__ = tname
            tool_func.__doc__ = desc
            return tool_func

        func = make_tool_func(server_name, tool_name, description)

        try:
            toolkit.register_tool_function(
                func,
                name=tool_name,
                description=description
            )
            logger.info(f"Registered MCP tool: {tool_name} (from {server_name})")
        except Exception as e:
            logger.error(f"Failed to register MCP tool '{tool_name}': {e}")

    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all available MCP tools"""
        tools_info = []
        for server_name, server_info in self.servers.items():
            for tool in server_info["tools"]:
                tools_info.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "server": server_name,
                    "schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                })
        return tools_info

    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        try:
            await self.exit_stack.aclose()
            self.servers.clear()
            self._connected = False
            logger.info("Disconnected from all MCP servers")
        except Exception as e:
            logger.error(f"Error disconnecting MCP servers: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tool_count(self) -> int:
        return sum(len(info["tools"]) for info in self.servers.values())
