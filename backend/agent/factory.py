"""Agent factory for creating AgentScope agents"""

import asyncio
from typing import Optional

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg

from config import get_settings
from agent.mcp_manager import MCPManager


class AgentFactory:
    """Factory for creating and configuring AgentScope agents"""

    def __init__(self):
        self.settings = get_settings()
        self.mcp_manager = MCPManager()
        self.toolkit = None  # Will be set after MCP connect

    async def initialize(self):
        """Initialize MCP connections and create toolkit"""
        await self.mcp_manager.connect_all()
        self.toolkit = self.mcp_manager.create_toolkit()

    def create_agent(
        self,
        name: str = "assistant",
        sys_prompt: Optional[str] = None,
        deep_research: bool = False
    ) -> ReActAgent:
        """Create a configured ReActAgent

        Args:
            name: Agent name
            sys_prompt: System prompt (uses default if None)
            deep_research: Enable deep thinking mode for research

        Returns:
            Configured ReActAgent instance
        """
        if sys_prompt is None:
            sys_prompt = (
                "你是一个支持多模态对话和深度研究的AI助手。"
                "你可以理解文本、图片和视频输入，"
                "能够生成文本、图片和分析视觉内容。"
                "在深度研究模式下，你会进行更深入的思考和分析。"
            )

        # Create model with appropriate settings
        model = DashScopeChatModel(
            model_name=self.settings.VISION_MODEL if deep_research else self.settings.CHAT_MODEL,
            api_key=self.settings.DASHSCOPE_API_KEY,
            stream=True,
            enable_thinking=deep_research and self.settings.ENABLE_DEEP_THINKING,
            temperature=self.settings.TEMPERATURE,
            top_p=self.settings.TOP_P,
        )

        # Create formatter for multimodal content
        formatter = DashScopeChatFormatter()

        # Create agent - pass toolkit if MCP tools are available
        # Toolkit API differs by version: try common attribute names
        _tools = (
            getattr(self.toolkit, "tools", None)
            or getattr(self.toolkit, "tool_list", None)
            or []
        )
        if self.toolkit and len(_tools) > 0:
            agent = ReActAgent(
                name=name,
                sys_prompt=sys_prompt,
                model=model,
                formatter=formatter,
                memory=InMemoryMemory(),
                max_iters=self.settings.MAX_AGENT_ITERATIONS,
                toolkit=self.toolkit,
            )
        else:
            agent = ReActAgent(
                name=name,
                sys_prompt=sys_prompt,
                model=model,
                formatter=formatter,
                memory=InMemoryMemory(),
                max_iters=self.settings.MAX_AGENT_ITERATIONS,
            )

        # Configure agent for streaming
        agent.set_console_output_enabled(False)
        agent.set_msg_queue_enabled(True, queue=asyncio.Queue())

        return agent

    async def shutdown(self):
        """Shutdown MCP connections"""
        await self.mcp_manager.disconnect_all()