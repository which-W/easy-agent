"""Session management for conversations"""

import time
import uuid
from typing import Dict, Optional, Any
from agentscope.agent import ReActAgent

from agent.factory import AgentFactory


class Session:
    """Represents a conversation session"""

    def __init__(self, session_id: str, agent: ReActAgent, persona: Optional[str] = None):
        self.session_id = session_id
        self.agent = agent
        self.persona = persona          # Store persona so callers can inspect it
        self.created_at = time.time()
        self.last_active = time.time()
        self.metadata: Dict[str, Any] = {}

    def touch(self):
        """Update last active time"""
        self.last_active = time.time()


class SessionManager:
    """Manage conversation sessions"""

    def __init__(self, ttl_seconds: int = 1800):  # 30 minutes
        self.sessions: Dict[str, Session] = {}
        self.factory = AgentFactory()
        self.ttl_seconds = ttl_seconds

    def get_or_create(
        self,
        session_id: Optional[str],
        deep_research: bool = False,
        has_multimodal: bool = False,
        persona: Optional[str] = None
    ) -> Session:
        """Get existing session or create new one.

        A new session is created whenever session_id is absent/unknown,
        OR when the requested persona differs from the existing session's persona
        (changing persona mid-conversation starts a fresh agent with the new prompt).

        Args:
            session_id: Session ID, creates new if None or not found
            deep_research: Whether to create agent in deep research mode
            has_multimodal: Whether the message contains images or videos
            persona: Custom system prompt / agent persona. None uses the default.

        Returns:
            Session object
        """
        # Clean expired sessions
        self._cleanup_expired()

        # Try to reuse existing session — but only if the persona hasn't changed
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if session.persona == persona:
                session.touch()
                return session
            # Persona changed: fall through to create a fresh agent below
            # (keeping the same session_id so the frontend stays in sync)

        # Build the system prompt from persona (or fall back to factory default)
        sys_prompt = self._build_sys_prompt(persona)

        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        agent = self.factory.create_agent(
            name="assistant",
            sys_prompt=sys_prompt,
            deep_research=deep_research,
            has_multimodal=has_multimodal
        )
        session = Session(new_session_id, agent, persona=persona)
        self.sessions[new_session_id] = session

        return session

    def _build_sys_prompt(self, persona: Optional[str]) -> Optional[str]:
        """Compose the full system prompt from the persona string.

        If persona is empty/None, returns None so factory uses its default.
        Otherwise wraps it with capability instructions.
        """
        if not persona or not persona.strip():
            return None

        return (
            f"{persona.strip()}\n\n"
            "你同时支持多模态对话：可以理解文本、图片和视频输入，"
            "能够生成文本、分析视觉内容。"
            "在深度研究模式下，你会进行更深入的思考和分析。"
        )

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions"""
        return {
            sid: {
                "created_at": s.created_at,
                "last_active": s.last_active,
                "metadata": s.metadata
            }
            for sid, s in self.sessions.items()
        }

    def _cleanup_expired(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired_ids = [
            sid for sid, session in self.sessions.items()
            if current_time - session.last_active > self.ttl_seconds
        ]
        for sid in expired_ids:
            del self.sessions[sid]
            print(f"Cleaned up expired session: {sid}")


# Global session manager instance
session_manager = SessionManager()