"""Session management for conversations"""

import time
import uuid
from typing import Dict, Optional, Any
from agentscope.agent import ReActAgent

from agent.factory import AgentFactory


class Session:
    """Represents a conversation session"""

    def __init__(self, session_id: str, agent: ReActAgent):
        self.session_id = session_id
        self.agent = agent
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

    def get_or_create(self, session_id: Optional[str], deep_research: bool = False) -> Session:
        """Get existing session or create new one

        Args:
            session_id: Session ID, creates new if None or not found
            deep_research: Whether to create agent in deep research mode

        Returns:
            Session object
        """
        # Clean expired sessions
        self._cleanup_expired()

        # Try to get existing session
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.touch()
            return session

        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        agent = self.factory.create_agent(
            name="assistant",
            deep_research=deep_research
        )
        session = Session(new_session_id, agent)
        self.sessions[new_session_id] = session

        return session

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
