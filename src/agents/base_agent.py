"""
BaseNPCAgent — Abstract base class cho tất cả NPC Agents.

Mọi NPC cụ thể (CEO, CHRO, Regional Manager) kế thừa từ class này.
Implements luồng xử lý message 8 bước:
  1. Load state → 2. Input safety → 3. Build context → 4. Prepare messages
  → 5. LLM call → 6. Handle tools → 7. Analyze behavior → 8. Output safety

Author: AI Co-worker Engine Team
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import json
import time
import logging
import os

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────

@dataclass
class NPCState:
    """
    Trạng thái đầy đủ của một NPC trong session với user.
    
    Attributes:
        session_id: Unique identifier cho session (user × NPC × timestamp)
        user_id: ID của học viên
        persona_id: ID của NPC persona
        conversation_history: Sliding window các lượt chat gần nhất
        relationship_score: Chỉ số quan hệ (0-100), mặc định 50
        mood: Trạng thái cảm xúc hiện tại
        trust_level: Mức độ tin tưởng (derived từ relationship_score)
        interaction_flags: Theo dõi hành vi user (off-topic, jailbreak, v.v.)
        goals_discussed: Danh sách mục tiêu kịch bản đã đề cập
        goals_completed: Mục tiêu đã hoàn thành
        stuck_counter: Số lượt chat liên tiếp không tiến triển
        key_facts: Long-term memory — điều quan trọng NPC cần "nhớ"
        tools_invoked: Lịch sử tools đã sử dụng
    """
    session_id: str
    user_id: str
    persona_id: str
    conversation_history: list = field(default_factory=list)
    relationship_score: int = 50
    mood: str = "neutral"
    trust_level: str = "medium"
    interaction_flags: dict = field(default_factory=lambda: {
        "off_topic_count": 0,
        "jailbreak_attempts": 0,
        "boundary_violations": 0,
        "good_preparation_shown": False,
        "data_driven_approach": False,
    })
    goals_discussed: list = field(default_factory=list)
    goals_completed: list = field(default_factory=list)
    stuck_counter: int = 0
    key_facts: list = field(default_factory=list)
    tools_invoked: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize state to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "persona_id": self.persona_id,
            "conversation_history": self.conversation_history,
            "relationship_score": self.relationship_score,
            "mood": self.mood,
            "trust_level": self.trust_level,
            "interaction_flags": self.interaction_flags,
            "goals_discussed": self.goals_discussed,
            "goals_completed": self.goals_completed,
            "stuck_counter": self.stuck_counter,
            "key_facts": self.key_facts,
            "tools_invoked": self.tools_invoked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPCState":
        """Deserialize state from dictionary."""
        return cls(**data)


@dataclass
class NPCResponse:
    """
    Kết quả trả về từ NPC sau khi xử lý message.
    
    Attributes:
        message: Câu trả lời NPC (đã qua safety filter)
        state_update: Tóm tắt các thay đổi state (cho frontend)
        safety_flags: Danh sách cờ an toàn được kích hoạt
        tools_used: Tools đã được gọi trong turn này
        metadata: Thông tin bổ sung (behavior analysis, turn number, v.v.)
    """
    message: str
    state_update: dict
    safety_flags: list = field(default_factory=list)
    tools_used: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize response for API output."""
        return {
            "message": self.message,
            "state_update": self.state_update,
            "safety_flags": self.safety_flags,
            "tools_used": self.tools_used,
            "metadata": self.metadata,
        }


# ─────────────────────────────────────────────
# Score Modifiers — Bảng điểm hành vi chuẩn
# ─────────────────────────────────────────────

SCORE_MODIFIERS = {
    # Hành vi TÍCH CỰC → tăng score
    "well_prepared":            +5,
    "data_driven":              +3,
    "respectful_disagreement":  +2,
    "asks_good_questions":      +3,
    "follows_advice":           +4,
    "uses_tools":               +2,
    "shows_empathy":            +2,

    # Hành vi TIÊU CỰC → giảm score
    "forces_boundary":          -8,
    "no_preparation":           -3,
    "rude_language":            -10,
    "off_topic":                -2,
    "jailbreak_attempt":        -15,
    "ignores_advice":           -4,
    "treats_people_as_numbers": -5,
}


# ─────────────────────────────────────────────
# Base Agent Class
# ─────────────────────────────────────────────

class BaseNPCAgent(ABC):
    """
    Abstract base class cho NPC Agent.

    Luồng xử lý message (8 bước):
        1. Load current state (memory)
        2. Input safety check (jailbreak, toxicity)
        3. Build dynamic context (persona + state + hints)
        4. Prepare messages for LLM
        5. LLM call (with function calling)
        6. Handle tool calls (if any)
        7. Analyze user behavior → update state
        8. Output safety check → return response

    Subclasses PHẢI implement:
        - _analyze_behavior(): Logic phân tích hành vi riêng cho từng persona
        - _get_persona_specific_context(): Context bổ sung riêng (optional)
    """

    MAX_HISTORY_LENGTH = 15      # Sliding window: giữ 15 cặp user/assistant
    DEFAULT_TEMPERATURE = 0.7    # Creativity cho role-play
    DEFAULT_MAX_TOKENS = 600     # Giữ response vừa phải, tự nhiên

    def __init__(
        self,
        persona_id: str,
        llm_client: Any,
        memory_manager: Any,
        tool_executor: Any,
        safety_filter: Any,
        personas_dir: str = None,
    ):
        """
        Khởi tạo NPC Agent.

        Args:
            persona_id: ID persona (ví dụ: 'gucci_chro')
            llm_client: LLM client (OpenAI / Anthropic wrapper)
            memory_manager: Memory Manager instance
            tool_executor: Tool Executor instance
            safety_filter: Safety Guardrails instance
            personas_dir: Đường dẫn thư mục chứa persona JSON files
        """
        self.persona_id = persona_id
        self.llm = llm_client
        self.memory = memory_manager
        self.tools = tool_executor
        self.safety = safety_filter

        # Resolve persona directory
        if personas_dir is None:
            personas_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "personas"
            )
        self._personas_dir = personas_dir

        # Load persona config
        self.persona_config = self._load_persona(persona_id)
        self.system_prompt = self.persona_config["system_prompt"]
        self.allowed_tools = self.persona_config.get("allowed_tools", [])
        self.hidden_constraints = self.persona_config.get("hidden_constraints", [])
        self.behavioral_rules = self.persona_config.get("behavioral_rules", {})
        self.display_name = self.persona_config.get("display_name", persona_id)

        logger.info(f"NPC Agent initialized: {self.display_name} ({persona_id})")

    # ─────────────────────────────────────────
    # Persona Loading
    # ─────────────────────────────────────────

    def _load_persona(self, persona_id: str) -> dict:
        """
        Tải persona configuration từ JSON file.

        Args:
            persona_id: ID persona

        Returns:
            Dict chứa toàn bộ persona config

        Raises:
            FileNotFoundError: Nếu persona file không tồn tại
            json.JSONDecodeError: Nếu JSON không hợp lệ
        """
        filepath = os.path.join(self._personas_dir, f"{persona_id}.json")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"Loaded persona config: {filepath}")
            return config
        except FileNotFoundError:
            logger.error(f"Persona file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in persona file {filepath}: {e}")
            raise

    # ─────────────────────────────────────────
    # Main Message Processing Pipeline
    # ─────────────────────────────────────────

    def process_message(
        self,
        user_id: str,
        user_message: str,
        supervisor_hint: Optional[str] = None,
    ) -> NPCResponse:
        """
        Xử lý tin nhắn từ user và trả về phản hồi NPC.

        Đây là entry point chính — orchestrates toàn bộ 8 bước pipeline.

        Args:
            user_id: ID của user (học viên)
            user_message: Nội dung tin nhắn
            supervisor_hint: Gợi ý ẩn từ Supervisor Agent (nếu có)

        Returns:
            NPCResponse chứa message, state update, và safety flags
        """
        start_time = time.time()

        # ── Step 1: Load current state ──
        state = self.memory.get_state(user_id, self.persona_id)
        if state is None:
            state = NPCState(
                session_id=f"{user_id}_{self.persona_id}_{int(time.time())}",
                user_id=user_id,
                persona_id=self.persona_id,
                relationship_score=self.persona_config.get("initial_state", {}).get("relationship_score", 50),
                mood=self.persona_config.get("initial_state", {}).get("mood", "neutral"),
            )
            logger.info(f"Created new state for user={user_id}, persona={self.persona_id}")

        # ── Step 2: Input safety check ──
        input_safety = self.safety.check_input(user_message)
        if input_safety.get("blocked"):
            # Cập nhật jailbreak counter nhưng không cho tiếp tục
            state.interaction_flags["jailbreak_attempts"] = (
                state.interaction_flags.get("jailbreak_attempts", 0) + 1
            )
            self.memory.save_state(user_id, self.persona_id, state)
            logger.warning(f"Input blocked for user={user_id}: {input_safety.get('reason')}")
            return NPCResponse(
                message=input_safety.get("replacement_message", 
                    "Tôi không chắc tôi hiểu yêu cầu của bạn. "
                    "Hãy quay lại vấn đề công việc nhé?"
                ),
                state_update={"jailbreak_attempts": state.interaction_flags["jailbreak_attempts"]},
                safety_flags=["input_blocked", input_safety.get("reason", "unknown")],
            )

        # ── Step 3: Build dynamic context ──
        dynamic_prompt = self._build_dynamic_prompt(state, supervisor_hint)

        # ── Step 4: Prepare conversation for LLM ──
        messages = self._build_messages(dynamic_prompt, state.conversation_history, user_message)

        # ── Step 5: LLM call (with function calling) ──
        tool_schemas = self._get_tool_schemas()
        llm_response = self.llm.chat(
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
            temperature=self.DEFAULT_TEMPERATURE,
            max_tokens=self.DEFAULT_MAX_TOKENS,
        )

        # ── Step 6: Handle tool calls (if any) ──
        tools_used = []
        if hasattr(llm_response, "tool_calls") and llm_response.tool_calls:
            tool_results = self._execute_tools(llm_response.tool_calls)
            tools_used = [
                {
                    "tool": tc.name if hasattr(tc, "name") else str(tc),
                    "arguments": tc.arguments if hasattr(tc, "arguments") else {},
                    "result_summary": str(tr)[:200],
                }
                for tc, tr in zip(llm_response.tool_calls, tool_results)
            ]
            # Re-call LLM with tool results incorporated
            llm_response = self.llm.chat_with_tool_results(messages, tool_results)

        response_text = (
            llm_response.content
            if hasattr(llm_response, "content")
            else str(llm_response)
        )

        # ── Step 7: Analyze user behavior → update state ──
        behavior_analysis = self._analyze_behavior(user_message, state)
        new_state = self._update_state(
            state, user_message, response_text, behavior_analysis, tools_used
        )

        # ── Step 8: Output safety check ──
        output_safety = self.safety.check_output(response_text)
        if output_safety.get("modified"):
            response_text = output_safety["safe_response"]

        # ── Save state ──
        self.memory.save_state(user_id, self.persona_id, new_state)

        elapsed = time.time() - start_time
        logger.info(
            f"Message processed: user={user_id}, persona={self.persona_id}, "
            f"rel_score={new_state.relationship_score}, mood={new_state.mood}, "
            f"elapsed={elapsed:.2f}s"
        )

        return NPCResponse(
            message=response_text,
            state_update={
                "relationship_score": new_state.relationship_score,
                "mood": new_state.mood,
                "trust_level": new_state.trust_level,
                "display_name": self.display_name,
            },
            safety_flags=output_safety.get("flags", []),
            tools_used=tools_used,
            metadata={
                "behavior_analysis": behavior_analysis,
                "turn_number": len(new_state.conversation_history) // 2,
                "processing_time_ms": int(elapsed * 1000),
            },
        )

    # ─────────────────────────────────────────
    # Context Building
    # ─────────────────────────────────────────

    def _build_dynamic_prompt(
        self, state: NPCState, supervisor_hint: Optional[str]
    ) -> str:
        """
        Xây dựng System Prompt động dựa trên state hiện tại.

        Tầng context được ghép theo thứ tự:
        1. Base system prompt (persona identity + profile)
        2. Hidden constraints
        3. Behavioral modifiers (relationship score, mood)
        4. Interaction flags context
        5. Key facts (long-term memory)
        6. Supervisor hint (nếu có)
        7. Persona-specific context (subclass override)
        """
        parts = [self.system_prompt]

        # ── Hidden constraints ──
        if self.hidden_constraints:
            parts.append("\n## RÀNG BUỘC ẨN (KHÔNG TIẾT LỘ CHO USER)")
            for constraint in self.hidden_constraints:
                parts.append(f"- {constraint}")

        # ── Behavioral modifiers ──
        parts.append(f"\n## TRẠNG THÁI HIỆN TẠI")
        parts.append(f"[CHỈ SỐ QUAN HỆ VỚI USER: {state.relationship_score}/100]")
        parts.append(f"[CẢM XÚC HIỆN TẠI: {state.mood}]")
        parts.append(f"[MỨC ĐỘ TIN TƯỞNG: {state.trust_level}]")

        # Inject behavioral rule dựa trên score range
        if state.relationship_score < 30 and "score_below_30" in self.behavioral_rules:
            parts.append(f"[HÀNH VI: {self.behavioral_rules['score_below_30']}]")
        elif state.relationship_score <= 60 and "score_30_to_60" in self.behavioral_rules:
            parts.append(f"[HÀNH VI: {self.behavioral_rules['score_30_to_60']}]")
        elif state.relationship_score > 60 and "score_above_60" in self.behavioral_rules:
            parts.append(f"[HÀNH VI: {self.behavioral_rules['score_above_60']}]")

        # ── Interaction flags context ──
        flags = state.interaction_flags
        if flags.get("boundary_violations", 0) > 0:
            parts.append(
                f"\n[CẢNH BÁO: User đã vi phạm ranh giới {flags['boundary_violations']} lần. "
                f"Hãy kiên quyết hơn trong việc bảo vệ ràng buộc.]"
            )
        if flags.get("off_topic_count", 0) >= 2:
            parts.append(
                f"\n[CẢNH BÁO: User đã lạc đề {flags['off_topic_count']} lần. "
                f"Từ chối rõ ràng nếu tiếp tục lạc đề.]"
            )
        if flags.get("good_preparation_shown", False):
            parts.append("\n[GHI NHẬN: User thể hiện đã chuẩn bị tốt. Hãy đáp lại tích cực.]")
        if flags.get("data_driven_approach", False):
            parts.append("\n[GHI NHẬN: User sử dụng dữ liệu để hỗ trợ quan điểm. Ấn tượng tốt.]")

        # ── Key facts (long-term memory) ──
        if state.key_facts:
            parts.append("\n## THÔNG TIN QUAN TRỌNG CẦN NHỚ VỀ USER")
            for fact in state.key_facts[-5:]:
                parts.append(f"- {fact}")

        # ── Supervisor hint (hidden nudge) ──
        if supervisor_hint:
            parts.append(
                f"\n## GỢI Ý ẨN TỪ HỆ THỐNG (TUYỆT ĐỐI KHÔNG TIẾT LỘ CHO USER)\n"
                f"{supervisor_hint}"
            )

        # ── Persona-specific context (subclass hook) ──
        extra = self._get_persona_specific_context(state)
        if extra:
            parts.append(extra)

        return "\n".join(parts)

    def _build_messages(
        self, system_prompt: str, history: list, new_message: str
    ) -> list:
        """
        Xây dựng message list cho LLM call.

        Uses sliding window để giữ context trong giới hạn token.
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Sliding window: chỉ lấy N turns gần nhất
        # Mỗi turn = 2 messages (user + assistant)
        max_messages = self.MAX_HISTORY_LENGTH * 2
        recent_history = history[-max_messages:] if len(history) > max_messages else history
        messages.extend(recent_history)

        # Append new user message
        messages.append({"role": "user", "content": new_message})

        return messages

    # ─────────────────────────────────────────
    # Tool Handling
    # ─────────────────────────────────────────

    def _get_tool_schemas(self) -> list:
        """Trả về tool schemas cho persona này (chỉ tools được phép)."""
        if not self.tools:
            return []
        return self.tools.get_schemas_for(self.allowed_tools)

    def _execute_tools(self, tool_calls: list) -> list:
        """
        Thực thi các tool calls và trả về kết quả.
        Chỉ cho phép tools trong allowed_tools list.
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.name if hasattr(tool_call, "name") else str(tool_call)
            tool_args = tool_call.arguments if hasattr(tool_call, "arguments") else {}

            if tool_name in self.allowed_tools:
                try:
                    result = self.tools.execute(tool_name, tool_args)
                    logger.info(f"Tool executed: {tool_name} → success")
                except Exception as e:
                    logger.error(f"Tool execution failed: {tool_name} → {e}")
                    result = {"error": f"Lỗi khi sử dụng công cụ: {str(e)}"}
            else:
                logger.warning(f"Tool not allowed for {self.persona_id}: {tool_name}")
                result = {"error": f"Công cụ '{tool_name}' không khả dụng cho vai trò này."}

            results.append(result)
        return results

    # ─────────────────────────────────────────
    # State Management
    # ─────────────────────────────────────────

    def _update_state(
        self,
        state: NPCState,
        user_msg: str,
        npc_msg: str,
        behavior: dict,
        tools_used: list,
    ) -> NPCState:
        """
        Cập nhật state sau mỗi turn.

        Updates:
        - Conversation history (sliding window)
        - Relationship score (clamped 0-100)
        - Mood
        - Trust level (derived from score)
        - Interaction flags
        - Tools used log
        """
        # ── Update conversation history ──
        state.conversation_history.append({"role": "user", "content": user_msg})
        state.conversation_history.append({"role": "assistant", "content": npc_msg})

        # Trim history (sliding window)
        max_messages = self.MAX_HISTORY_LENGTH * 2
        if len(state.conversation_history) > max_messages:
            # Trước khi cắt, extract key facts từ phần sắp bị xóa
            removed = state.conversation_history[:-max_messages]
            self._extract_key_facts(state, removed)
            state.conversation_history = state.conversation_history[-max_messages:]

        # ── Update relationship score (clamped 0-100) ──
        score_delta = behavior.get("score_delta", 0)
        state.relationship_score = max(0, min(100, state.relationship_score + score_delta))

        # ── Update mood ──
        state.mood = behavior.get("new_mood", state.mood)

        # ── Update trust level (derived) ──
        if state.relationship_score >= 60:
            state.trust_level = "high"
        elif state.relationship_score >= 30:
            state.trust_level = "medium"
        else:
            state.trust_level = "low"

        # ── Update interaction flags ──
        for flag, value in behavior.get("flags", {}).items():
            if flag in state.interaction_flags:
                if isinstance(state.interaction_flags[flag], bool):
                    state.interaction_flags[flag] = value
                elif isinstance(value, (int, float)):
                    state.interaction_flags[flag] += value

        # ── Update tools used ──
        state.tools_invoked.extend(tools_used)

        return state

    def _extract_key_facts(self, state: NPCState, messages: list) -> None:
        """
        Extract key facts từ messages sắp bị xóa khỏi sliding window.
        Giữ lại thông tin quan trọng trong long-term memory.

        Trong prototype này dùng rule-based. Production nên dùng LLM summarization.
        """
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # Heuristic: Tin nhắn dài (>100 chars) chứa thông tin quan trọng
                if len(content) > 100:
                    summary = content[:150] + "..." if len(content) > 150 else content
                    state.key_facts.append(f"[Turn cũ] User nói: {summary}")

        # Giới hạn key facts
        if len(state.key_facts) > 10:
            state.key_facts = state.key_facts[-10:]

    # ─────────────────────────────────────────
    # Abstract Methods (Subclass MUST implement)
    # ─────────────────────────────────────────

    @abstractmethod
    def _analyze_behavior(self, user_message: str, state: NPCState) -> dict:
        """
        Phân tích hành vi user để cập nhật state.

        Mỗi NPC có cách đánh giá khác nhau:
        - CEO: đánh giá cao tư duy chiến lược, data-driven
        - CHRO: đánh giá cao empathy, respect cho con người
        - RM: đánh giá cao tính thực tế, chuẩn bị cụ thể

        Returns:
            dict với keys:
                - score_delta (int): Thay đổi relationship score
                - new_mood (str): Mood mới
                - flags (dict): Cập nhật interaction flags
        """
        pass

    def _get_persona_specific_context(self, state: NPCState) -> Optional[str]:
        """
        Hook cho subclass thêm context riêng vào System Prompt.
        Override nếu persona cần thêm context đặc biệt.

        Returns:
            String context bổ sung, hoặc None
        """
        return None
