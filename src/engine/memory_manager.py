"""
MemoryManager — Quản lý trí nhớ và trạng thái cho NPC Agents.

Hỗ trợ 2 storage backends:
- InMemoryStore: Cho prototype/testing (mặc định)
- RedisStore: Cho production (optional)

Author: AI Co-worker Engine Team
"""

from typing import Optional, Any
import json
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class InMemoryStore:
    """
    In-memory storage backend cho prototype.
    Lưu state trong dict — mất khi restart server.
    """

    def __init__(self):
        # Key format: "{user_id}::{persona_id}"
        self._states: dict[str, dict] = {}
        # Cross-NPC events: key = user_id
        self._cross_npc_events: dict[str, list] = defaultdict(list)
        logger.info("InMemoryStore initialized")

    def get(self, key: str) -> Optional[dict]:
        return self._states.get(key)

    def set(self, key: str, value: dict) -> None:
        self._states[key] = value

    def delete(self, key: str) -> None:
        self._states.pop(key, None)

    def get_cross_events(self, user_id: str) -> list:
        return self._cross_npc_events.get(user_id, [])

    def add_cross_event(self, user_id: str, event: dict) -> None:
        self._cross_npc_events[user_id].append(event)
        # Giới hạn events
        if len(self._cross_npc_events[user_id]) > 50:
            self._cross_npc_events[user_id] = self._cross_npc_events[user_id][-50:]

    def list_sessions(self, user_id: str) -> list:
        """Liệt kê tất cả persona sessions của một user."""
        prefix = f"{user_id}::"
        return [
            key.split("::")[1]
            for key in self._states
            if key.startswith(prefix)
        ]


class MemoryManager:
    """
    Quản lý trí nhớ và trạng thái cho NPC Agents.

    Responsibilities:
    1. Lưu/tải NPCState cho mỗi cặp (user, persona)
    2. Quản lý cross-NPC shared context
    3. Cung cấp conversation history cho Supervisor
    4. Audit logging

    Usage:
        memory = MemoryManager()
        state = memory.get_state("user_123", "gucci_chro")
        # ... modify state ...
        memory.save_state("user_123", "gucci_chro", state)
    """

    def __init__(self, store: Optional[Any] = None):
        """
        Args:
            store: Storage backend. Mặc định: InMemoryStore.
                   Có thể inject RedisStore cho production.
        """
        self.store = store or InMemoryStore()
        logger.info(f"MemoryManager initialized with {type(self.store).__name__}")

    def _make_key(self, user_id: str, persona_id: str) -> str:
        """Tạo storage key từ user_id và persona_id."""
        return f"{user_id}::{persona_id}"

    # ─────────────────────────────────────────
    # State CRUD
    # ─────────────────────────────────────────

    def get_state(self, user_id: str, persona_id: str):
        """
        Tải NPCState cho một cặp (user, persona).

        Returns:
            NPCState nếu tồn tại, None nếu chưa có session.
        """
        # Import here to avoid circular dependency
        from src.agents.base_agent import NPCState

        key = self._make_key(user_id, persona_id)
        data = self.store.get(key)
        if data is None:
            logger.debug(f"No existing state for {key}")
            return None

        try:
            return NPCState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to deserialize state for {key}: {e}")
            return None

    def save_state(self, user_id: str, persona_id: str, state) -> None:
        """
        Lưu NPCState.

        Args:
            user_id: ID học viên
            persona_id: ID persona
            state: NPCState instance
        """
        key = self._make_key(user_id, persona_id)
        try:
            self.store.set(key, state.to_dict())
            logger.debug(
                f"State saved: {key}, rel_score={state.relationship_score}, "
                f"mood={state.mood}, history_len={len(state.conversation_history)}"
            )
        except Exception as e:
            logger.error(f"Failed to save state for {key}: {e}")
            raise

    def delete_state(self, user_id: str, persona_id: str) -> None:
        """Xóa state (reset session)."""
        key = self._make_key(user_id, persona_id)
        self.store.delete(key)
        logger.info(f"State deleted: {key}")

    def reset_all_states(self, user_id: str) -> None:
        """Reset tất cả sessions của một user."""
        sessions = self.store.list_sessions(user_id)
        for persona_id in sessions:
            self.delete_state(user_id, persona_id)
        logger.info(f"All states reset for user={user_id}")

    # ─────────────────────────────────────────
    # Cross-NPC Shared Context
    # ─────────────────────────────────────────

    def add_cross_npc_event(
        self,
        user_id: str,
        source_persona: str,
        summary: str,
        key_outcome: Optional[dict] = None,
    ) -> None:
        """
        Ghi nhận sự kiện cross-NPC để các NPC khác biết context.

        Ví dụ: Nếu user nói với CHRO rằng "CEO đã đồng ý", CHRO có thể
        kiểm tra cross-NPC events để verify.

        Args:
            user_id: ID học viên
            source_persona: NPC nào ghi nhận event
            summary: Tóm tắt sự kiện
            key_outcome: Dict kết quả quan trọng (optional)
        """
        event = {
            "source_persona": source_persona,
            "summary": summary,
            "key_outcome": key_outcome or {},
            "timestamp": time.time(),
        }
        self.store.add_cross_event(user_id, event)
        logger.debug(f"Cross-NPC event added: {source_persona} → {summary[:80]}")

    def get_cross_npc_events(
        self, user_id: str, limit: int = 10
    ) -> list:
        """
        Lấy cross-NPC events gần nhất cho một user.

        Args:
            user_id: ID học viên
            limit: Số events tối đa

        Returns:
            List of event dicts, mới nhất trước.
        """
        events = self.store.get_cross_events(user_id)
        return events[-limit:]

    # ─────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────

    def get_conversation_history(
        self, user_id: str, persona_id: str, last_n: int = 10
    ) -> list:
        """
        Lấy N lượt chat gần nhất (cho Supervisor analysis).

        Returns:
            List of message dicts [{"role": "user"/"assistant", "content": "..."}]
        """
        state = self.get_state(user_id, persona_id)
        if state is None:
            return []
        return state.conversation_history[-last_n * 2:]

    def get_all_active_personas(self, user_id: str) -> list:
        """Lấy danh sách tất cả personas mà user đã tương tác."""
        return self.store.list_sessions(user_id)

    def get_relationship_scores(self, user_id: str) -> dict:
        """
        Lấy relationship scores của user với tất cả NPCs.

        Returns:
            Dict mapping persona_id → relationship_score
        """
        scores = {}
        for persona_id in self.store.list_sessions(user_id):
            state = self.get_state(user_id, persona_id)
            if state:
                scores[persona_id] = {
                    "relationship_score": state.relationship_score,
                    "mood": state.mood,
                    "trust_level": state.trust_level,
                }
        return scores
