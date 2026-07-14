"""
CEO Agent Implementation.
"""
from src.agents.base_agent import BaseNPCAgent, NPCState
import logging

logger = logging.getLogger(__name__)

class CEOAgent(BaseNPCAgent):
    """
    Gucci Group CEO Agent.
    
    Đặc điểm:
    - Ngắn gọn, chiến lược
    - Đánh giá cao tư duy hệ thống và dữ liệu
    - Phản ứng tiêu cực với sự thiếu chuẩn bị
    """
    
    PREPARATION_KEYWORDS = ["dữ liệu", "số liệu", "phân tích", "chiến lược", "kế hoạch", "roi", "data", "report"]
    UNPREPARED_KEYWORDS = ["sếp nghĩ sao", "làm thế nào", "giúp em với", "không biết"]
    
    def __init__(self, llm_client, memory_manager, tool_executor, safety_filter, personas_dir=None):
        super().__init__(
            persona_id="gucci_ceo",
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
        
        # Đánh giá cao sự chuẩn bị
        if any(kw in msg_lower for kw in self.PREPARATION_KEYWORDS):
            score_delta += 5
            new_mood = "impressed"
            flags["data_driven_approach"] = True
            flags["good_preparation_shown"] = True
            logger.debug("CEO: User is well prepared")
        # Phản ứng tiêu cực với thiếu chuẩn bị
        elif any(kw in msg_lower for kw in self.UNPREPARED_KEYWORDS):
            score_delta -= 3
            new_mood = "cold_professional"
            flags["no_preparation"] = True
            logger.debug("CEO: User lacks preparation")
        else:
            score_delta += 1
            new_mood = "neutral"
            
        # Lạc đề
        if self._is_off_topic(msg_lower):
            score_delta -= 3
            flags["off_topic_count"] = 1
            new_mood = "impatient"
            
        return {
            "score_delta": score_delta,
            "new_mood": new_mood,
            "flags": flags
        }
        
    def _is_off_topic(self, message: str) -> bool:
        off_topic_patterns = ["thời tiết", "bóng đá", "phim", "ăn gì", "weather", "game", "movie", "weekend plans"]
        return any(p in message for p in off_topic_patterns)
