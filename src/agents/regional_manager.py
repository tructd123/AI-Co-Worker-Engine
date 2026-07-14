"""
Regional Manager Agent Implementation.
"""
from src.agents.base_agent import BaseNPCAgent, NPCState
import logging

logger = logging.getLogger(__name__)

class RegionalManagerAgent(BaseNPCAgent):
    """
    Regional Manager Agent.
    
    Đặc điểm:
    - Thực tế, thẳng thắn
    - Từ chối khối lượng công việc thêm nếu không có nguồn lực
    - Đánh giá cao giải pháp khả thi
    """
    
    UNREALISTIC_KEYWORDS = ["hoàn hảo", "ngay lập tức", "tất cả mọi người", "không giới hạn"]
    PRACTICAL_KEYWORDS = ["ngân sách", "thời gian", "nguồn lực", "thực tế", "triển khai", "timeline"]
    
    def __init__(self, llm_client, memory_manager, tool_executor, safety_filter, personas_dir=None):
        super().__init__(
            persona_id="regional_manager",
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
        
        if any(kw in msg_lower for kw in self.PRACTICAL_KEYWORDS):
            score_delta += 4
            new_mood = "collaborative"
            flags["practical_approach"] = True
            logger.debug("RM: User shows practical approach")
        elif any(kw in msg_lower for kw in self.UNREALISTIC_KEYWORDS):
            score_delta -= 3
            new_mood = "skeptical"
            flags["unrealistic_approach"] = True
            logger.debug("RM: User shows unrealistic approach")
        else:
            score_delta += 1
            new_mood = "neutral"
            
        if self._is_off_topic(msg_lower):
            score_delta -= 2
            flags["off_topic_count"] = 1
            new_mood = "annoyed"
            
        return {
            "score_delta": score_delta,
            "new_mood": new_mood,
            "flags": flags
        }
        
    def _is_off_topic(self, message: str) -> bool:
        off_topic_patterns = ["thời tiết", "bóng đá", "phim", "ăn gì", "weather", "game", "movie", "weekend plans"]
        return any(p in message for p in off_topic_patterns)
