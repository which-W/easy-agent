"""Agent factory for creating AgentScope agents

Key change vs. the original:
  The original factory created agents WITHOUT registering any tool functions,
  so agents could only chat — they never actually executed file operations.

  This version:
    1. Builds a Toolkit and registers all file / shell tools.
    2. Passes the populated Toolkit to every ReActAgent it creates.
    3. Keeps full backward-compatibility with the rest of the codebase
       (MCPManager, settings, multimodal flags, deep-research mode, etc.).
"""

import asyncio
from typing import Optional

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.tool import (
    Toolkit,
    # Built-in AgentScope 1.0.18 file tools
    write_text_file,
    view_text_file,
    insert_text_file,
    execute_python_code,
    execute_shell_command,
)

# Our custom tools defined in file_tools.py
from agent.file_tools import (
    create_file,
    read_file,
    edit_file,
    append_to_file,
    delete_file,
    list_directory,
    make_directory,
    move_file,
    copy_file,
    run_python_file,
    run_shell_command,
)

from config import get_settings
from agent.mcp_manager import MCPManager


# ---------------------------------------------------------------------------
# Default system prompt
# ---------------------------------------------------------------------------

_DEFAULT_SYS_PROMPT = """\
你是一个能够真正操作文件和执行代码的 AI 助手。

## 工具使用原则
- 当用户要求创建、修改或删除文件时，**立即调用相应工具执行**，不要只用文字描述步骤。
- 创建文件后，用 read_file 确认内容已正确写入。
- 执行代码前，先用 list_directory 或 read_file 确认文件存在。
- 遇到错误时，读取错误信息并尝试修复，不要直接放弃。

## 能力
- 理解文本、图片和视频输入
- 创建、读取、编辑、删除文件及目录
- 执行 Python 代码和 Shell 命令
- 在深度研究模式下进行更深入的思考与分析
"""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class AgentFactory:
    """Factory for creating and configuring AgentScope agents.

    Changes from original
    ---------------------
    * ``_build_toolkit()`` registers all file / execution tools so agents
      actually perform operations rather than just describing them.
    * ``create_agent()`` always receives a populated Toolkit.
    """

    def __init__(self):
        self.settings = get_settings()
        self.mcp_manager = MCPManager()
        self.toolkit: Optional[Toolkit] = None  # populated by initialize()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self):
        """Connect MCP servers then build the Toolkit."""
        await self.mcp_manager.connect_all()
        self.toolkit = self._build_toolkit()

    async def shutdown(self):
        """Disconnect all MCP connections."""
        await self.mcp_manager.disconnect_all()

    # ------------------------------------------------------------------
    # Toolkit construction  ← THE KEY FIX
    # ------------------------------------------------------------------

    def _build_toolkit(self) -> Toolkit:
        """Create a Toolkit pre-loaded with file-operation and execution tools.

        Tool registration order:
          1. Built-in AgentScope tools  (write_text_file, view_text_file, …)
          2. Custom tools from file_tools.py
          3. MCP tools (if any MCP servers are connected)

        Every tool function must be an async function returning ToolResponse;
        register_tool_function() auto-generates the JSON schema from the
        Google-style docstring, which the model uses to decide when/how to
        call each tool.
        """
        toolkit = Toolkit()

        # ── 1. Built-in AgentScope file tools ──────────────────────────
        # These are thin async wrappers already shaped as ToolResponse.
        builtin_tools = [
            write_text_file,      # create / overwrite
            view_text_file,       # read with line numbers
            insert_text_file,     # insert lines at position
            execute_python_code,  # run inline Python snippet
            execute_shell_command,  # run a shell command
        ]
        for fn in builtin_tools:
            toolkit.register_tool_function(fn)

        # ── 2. Custom file-operation tools ──────────────────────────────
        # Richer wrappers with clearer docstrings for better LLM calling.
        custom_tools = [
            create_file,       # create / overwrite with mkdir -p
            read_file,         # read with numbered lines
            edit_file,         # replace a line range
            append_to_file,    # append to end
            delete_file,       # delete permanently
            list_directory,    # ls with size info
            make_directory,    # mkdir -p
            move_file,         # mv
            copy_file,         # cp
            run_python_file,   # run a saved .py file
            run_shell_command, # run shell (alias with tighter timeout)
        ]
        for fn in custom_tools:
            toolkit.register_tool_function(
                fn,
                namesake_strategy="skip",   # skip if same name already registered
            )

        # ── 3. MCP tools (optional, from connected servers) ────────────
        for server_name, server_info in self.mcp_manager.servers.items():
            for tool in server_info["tools"]:
                self.mcp_manager._register_mcp_tool(
                    toolkit,
                    server_name=server_name,
                    tool_name=tool.name,
                    description=tool.description or f"MCP tool: {tool.name}",
                )

        registered = [s["function"]["name"] for s in toolkit.get_json_schemas()]
        print(f"[AgentFactory] Toolkit ready — {len(registered)} tools: "
              + ", ".join(registered))
        return toolkit

    # ------------------------------------------------------------------
    # Agent creation
    # ------------------------------------------------------------------

    def create_agent(
        self,
        name: str = "assistant",
        sys_prompt: Optional[str] = None,
        deep_research: bool = False,
        has_multimodal: bool = False,
    ) -> ReActAgent:
        """Create a configured ReActAgent with the pre-built Toolkit.

        Args:
            name: Agent name shown in logs / memory.
            sys_prompt: System prompt; uses _DEFAULT_SYS_PROMPT if None.
            deep_research: Enables thinking mode and selects the vision model.
            has_multimodal: Message contains images or video → vision model.

        Returns:
            Configured ReActAgent ready for streaming via msg_queue.
        """
        if sys_prompt is None:
            sys_prompt = _DEFAULT_SYS_PROMPT

        # Model selection: VL model for thinking / multimodal, chat otherwise
        use_vision_model = deep_research or has_multimodal
        model = DashScopeChatModel(
            model_name=(
                self.settings.VISION_MODEL
                if use_vision_model
                else self.settings.CHAT_MODEL
            ),
            api_key=self.settings.DASHSCOPE_API_KEY,
            stream=True,
            enable_thinking=deep_research and self.settings.ENABLE_DEEP_THINKING,
            temperature=self.settings.TEMPERATURE,
            top_p=self.settings.TOP_P,
        )

        formatter = DashScopeChatFormatter()

        # Guard: if initialize() was never called, build a minimal toolkit now
        # so the agent always has its tools (e.g. in tests or CLI use).
        if self.toolkit is None:
            print("[AgentFactory] Warning: initialize() not called — "
                  "building toolkit without MCP connections.")
            self.toolkit = self._build_toolkit()

        agent = ReActAgent(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            max_iters=self.settings.MAX_AGENT_ITERATIONS,
            toolkit=self.toolkit,   # ← always pass the populated toolkit
        )

        # Enable streaming via async queue
        agent.set_console_output_enabled(False)
        agent.set_msg_queue_enabled(True, queue=asyncio.Queue())

        return agent