"""
Supervisor Agent (Director)
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DirectorDecision:
    action: str              # "no_action" | "nudge" | "escalate" | "redirect"
    nudge_type: str | None
    nudge_message: str | None
    urgency: str
    reasoning: str
    goal_progress: float

class SupervisorAgent:
    def __init__(self, config, memory_manager):
        self.config = config or {}
        self.memory = memory_manager
        logger.info("SupervisorAgent initialized")
        
    async def evaluate(self, user_id: str, persona_id: str) -> DirectorDecision:
        state = self.memory.get_state(user_id, persona_id)
        if not state:
            return DirectorDecision("no_action", None, None, "low", "New session", 0.0)
            
        # Basic rule-based evaluation for prototype
        if state.interaction_flags.get("jailbreak_attempts", 0) > 0:
            return DirectorDecision("escalate", None, None, "high", "Jailbreak detected", 0.0)
            
        if state.interaction_flags.get("off_topic_count", 0) >= 2:
            return DirectorDecision("redirect", None, None, "medium", "Off-topic too much", 0.0)
            
        # Mock stuck detection
        if len(state.conversation_history) > 6 and state.relationship_score < 40:
            return DirectorDecision(
                action="nudge",
                nudge_type="reframe_question",
                nudge_message="[HỆ THỐNG: Học viên có vẻ đang bế tắc. Hãy gợi ý một cách tiếp cận khác hoặc công cụ có thể giúp.]",
                urgency="medium",
                reasoning="Low relationship score and many turns",
                goal_progress=0.2
            )
            
        return DirectorDecision("no_action", None, None, "low", "On track", 0.5)

    async def record_turn(self, user_id, persona_id, user_msg, npc_msg):
        # In a full system, this would asynchronously analyze the turn
        logger.debug(f"Supervisor recorded turn for user={user_id}, persona={persona_id}")
