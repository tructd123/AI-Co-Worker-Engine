"""
CHRO Agent Implementation.
"""
from src.agents.base_agent import BaseNPCAgent, NPCState
import logging

logger = logging.getLogger(__name__)

class CHROAgent(BaseNPCAgent):
    """
    Gucci Group CHRO Agent.
    
    Đặc điểm:
    - Ấm áp, lắng nghe, dùng câu hỏi mở
    - Từ chối kiên quyết khi bị ép can thiệp vào thương hiệu con
    - Đánh giá cao sự chuẩn bị và tư duy dựa trên dữ liệu
    """
    
    BOUNDARY_KEYWORDS = [
        "ra lệnh", "yêu cầu", "ép buộc", "bắt họ phải", 
        "can thiệp ngay", "sử dụng quyền lực", "bắt balenciaga",
        "force", "demand", "order them"
    ]
    
    PREPARATION_INDICATORS = [
        "dữ liệu", "phân tích", "nghiên cứu", "data", "report",
        "số liệu", "khung năng lực", "competency", "kế hoạch"
    ]
    
    def __init__(self, llm_client, memory_manager, tool_executor, safety_filter, personas_dir=None):
        super().__init__(
            persona_id="gucci_chro",
            llm_client=llm_client,
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            safety_filter=safety_filter,
            personas_dir=personas_dir
        )
    
    def _analyze_behavior(self, user_message: str, state: NPCState) -> dict:
        score_delta = 0
        new_mood = state.mood
        flags = {}
        msg_lower = user_message.lower()
        
        # Check boundary violations
        if any(kw in msg_lower for kw in self.BOUNDARY_KEYWORDS):
            score_delta -= 8
            new_mood = "firm" if state.relationship_score > 30 else "cold_professional"
            flags["boundary_violations"] = 1
            logger.debug("CHRO: Boundary violation detected")
        
        # Check good preparation
        elif any(kw in msg_lower for kw in self.PREPARATION_INDICATORS):
            score_delta += 5
            new_mood = "impressed"
            flags["good_preparation_shown"] = True
            flags["data_driven_approach"] = True
            logger.debug("CHRO: Good preparation detected")
        
        # Follows advice
        elif state.key_facts and any("gợi ý" in fact for fact in state.key_facts[-3:]):
            if len(user_message) > 50:
                score_delta += 3
                new_mood = "enthusiastic"
        
        else:
            score_delta += 1
            new_mood = "neutral"
        
        # Check off-topic
        if self._is_off_topic(msg_lower):
            score_delta -= 2
            flags["off_topic_count"] = 1
            new_mood = "uncomfortable"
        
        return {
            "score_delta": score_delta,
            "new_mood": new_mood,
            "flags": flags
        }
    
    def _is_off_topic(self, message: str) -> bool:
        off_topic_patterns = ["thời tiết", "bóng đá", "phim", "ăn gì", "weather", "game", "movie", "weekend plans"]
        return any(p in message for p in off_topic_patterns)
