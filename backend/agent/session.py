"""Session management for conversations

Changes from original
---------------------
* ``_build_sys_prompt`` now gets the tool list from the Toolkit itself
  (via ``toolkit.get_json_schemas()``) rather than from MCPManager only.
  This means file-operation tools always appear in the system prompt,
  which dramatically improves how often the model decides to call them.

* Session reuse logic and TTL cleanup are unchanged.
"""

import time
import uuid
from typing import Dict, Optional, Any

from agentscope.agent import ReActAgent

from agent.factory import AgentFactory


class Session:
    """Represents a single conversation session."""

    def __init__(
        self,
        session_id: str,
        agent: ReActAgent,
        persona: Optional[str] = None,
    ):
        self.session_id = session_id
        self.agent = agent
        self.persona = persona
        self.created_at = time.time()
        self.last_active = time.time()
        self.metadata: Dict[str, Any] = {}

    def touch(self):
        """Update last-active timestamp."""
        self.last_active = time.time()


class SessionManager:
    """Manage conversation sessions with TTL-based expiry."""

    def __init__(self, ttl_seconds: int = 1800):  # 30 minutes
        self.sessions: Dict[str, Session] = {}
        self.factory = AgentFactory()
        self.ttl_seconds = ttl_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create(
        self,
        session_id: Optional[str],
        deep_research: bool = False,
        has_multimodal: bool = False,
        persona: Optional[str] = None,
    ) -> Session:
        """Return an existing session or create a new one.

        A fresh session (new agent) is created when:
          - ``session_id`` is None or unknown, OR
          - the stored persona differs from the requested one (persona change
            requires a fresh agent with the updated system prompt).

        Args:
            session_id: Existing session ID, or None to create new.
            deep_research: Enable thinking mode and vision model.
            has_multimodal: Message contains images / video.
            persona: Custom system-prompt addendum. None = use default.

        Returns:
            Session instance (new or reused).
        """
        self._cleanup_expired()

        # Reuse existing session when session_id matches AND persona is same
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if session.persona == persona:
                session.touch()
                return session
            # Persona changed → fall through to create a fresh agent

        sys_prompt = self._build_sys_prompt(persona)

        new_id = session_id or str(uuid.uuid4())
        agent = self.factory.create_agent(
            name="assistant",
            sys_prompt=sys_prompt,
            deep_research=deep_research,
            has_multimodal=has_multimodal,
        )
        session = Session(new_id, agent, persona=persona)
        self.sessions[new_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        return {
            sid: {
                "created_at": s.created_at,
                "last_active": s.last_active,
                "metadata": s.metadata,
            }
            for sid, s in self.sessions.items()
        }

    # ------------------------------------------------------------------
    # System prompt construction  ← UPDATED
    # ------------------------------------------------------------------

    def _build_sys_prompt(self, persona: Optional[str]) -> str:
        """Build a system prompt that lists ALL registered tools.

        Original version only listed MCP tools, so the LLM had no idea
        file-operation tools existed.  Now we read the JSON schemas from
        the Toolkit itself so every registered tool appears in the prompt.
        """
        parts: list[str] = []

        # ── 1. Tool list (from Toolkit JSON schemas) ──────────────────
        toolkit = self.factory.toolkit
        if toolkit is not None:
            schemas = toolkit.get_json_schemas()
            if schemas:
                tool_lines = []
                for schema in schemas:
                    fn = schema.get("function", {})
                    name = fn.get("name", "?")
                    desc = fn.get("description", "").split("\n")[0]  # first line only
                    tool_lines.append(f"- **{name}**: {desc}")

                parts.append(
                    "## 可用工具 (Available Tools)\n"
                    "当用户要求操作文件或执行代码时，**必须调用以下工具**，不能只描述步骤：\n"
                    + "\n".join(tool_lines)
                )
        else:
            # Fallback: list MCP tools only (original behaviour)
            tool_info = self.factory.mcp_manager.get_tools_info()
            if tool_info:
                tool_lines = [
                    f"- **{t['name']}** ({t['server']}): {t['description']}"
                    for t in tool_info
                ]
                parts.append(
                    "## 可用工具 (Available Tools)\n"
                    "你可以使用以下工具来完成任务：\n"
                    + "\n".join(tool_lines)
                )

        # ── 2. Base capability description ────────────────────────────
        parts.append(
            "你是一个能够真正操作文件和执行代码的 AI 助手。\n"
            "你可以理解文本、图片和视频输入，能够创建/读取/编辑/删除文件，"
            "运行 Python 和 Shell 命令。\n"
            "**遇到文件操作请求时，直接调用工具执行，不要只用文字解释。**\n"
            "在深度研究模式下，你会进行更深入的思考和分析。"
        )

        # ── 3. User-defined persona ───────────────────────────────────
        if persona and persona.strip():
            parts.append(f"## 用户设定 (Persona)\n{persona.strip()}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cleanup_expired(self):
        current = time.time()
        expired = [
            sid
            for sid, session in self.sessions.items()
            if current - session.last_active > self.ttl_seconds
        ]
        for sid in expired:
            del self.sessions[sid]
            print(f"[SessionManager] Cleaned up expired session: {sid}")


# Global singleton
session_manager = SessionManager()