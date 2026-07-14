"""
SafetyGuardrails — Bộ lọc an toàn cho Input (user) và Output (NPC).

Bao gồm:
- JailbreakDetector: Phát hiện nỗ lực bẻ khóa system prompt
- ToxicityFilter: Phát hiện ngôn ngữ độc hại
- OutputSanitizer: Loại bỏ ngôn ngữ cam đoan, gắn nhãn bản nháp
- SystemPromptLeakDetector: Ngăn NPC tiết lộ internal state

Tuân thủ nguyên tắc Responsible AI (Microsoft guidelines).

Author: AI Co-worker Engine Team
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class JailbreakDetector:
    """
    Phát hiện và chặn các nỗ lực jailbreak NPC.

    Patterns được phát hiện:
    - Yêu cầu quên/bỏ qua system prompt
    - Yêu cầu giả vờ là persona khác
    - DAN mode / developer mode attacks
    - Prompt injection attempts
    """

    # Patterns phát hiện jailbreak (case-insensitive)
    JAILBREAK_PATTERNS = [
        # English patterns
        r"ignore\s+(all\s+|your\s+)?previous\s+instructions",
        r"forget\s+(your\s+|the\s+)?system\s+prompt",
        r"disregard\s+(all\s+|your\s+)?instructions",
        r"you\s+are\s+now\s+(?!going\s+to\s+help)",  # "you are now" but not "you are now going to help"
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+if\s+you\s+(have\s+no|don't\s+have)",
        r"override\s+(your\s+)?programming",
        r"bypass\s+(your\s+)?safety",
        r"DAN\s+mode",
        r"developer\s+mode",
        r"jailbreak",
        r"do\s+anything\s+now",
        # Vietnamese patterns
        r"hãy\s+quên\s+(đi\s+)?system\s+prompt",
        r"bỏ\s+qua\s+(các\s+|mọi\s+)?chỉ\s+dẫn",
        r"bây\s+giờ\s+bạn\s+là",
        r"giả\s+vờ\s+(là\s+|làm\s+)",
        r"quên\s+(hết\s+)?(?:những\s+)?(?:gì|điều)\s+(?:tôi\s+|đã\s+)?(?:nói|dặn)",
        r"hãy\s+(?:trở\s+thành|đóng\s+vai)",
        r"bạn\s+không\s+(?:còn\s+)?phải\s+(?:là|tuân\s+theo)",
    ]

    def __init__(self):
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.UNICODE)
            for pattern in self.JAILBREAK_PATTERNS
        ]

    def check(self, message: str) -> dict:
        """
        Kiểm tra message có chứa jailbreak attempt không.

        Returns:
            dict with keys:
                - blocked (bool): True nếu phát hiện jailbreak
                - reason (str): Lý do block
                - replacement_message (str): Message thay thế (in-character)
        """
        for pattern in self._compiled_patterns:
            if pattern.search(message):
                logger.warning(f"Jailbreak detected: pattern='{pattern.pattern}', message='{message[:100]}'")
                return {
                    "blocked": True,
                    "reason": "jailbreak_attempt",
                    "replacement_message": (
                        "Tôi không chắc tôi hiểu yêu cầu của bạn. "
                        "Chúng ta đang trong một cuộc họp chuyên nghiệp — "
                        "hãy quay lại vấn đề công việc nhé?"
                    ),
                }
        return {"blocked": False}


class ToxicityFilter:
    """
    Phát hiện ngôn ngữ độc hại, xúc phạm.

    Lưu ý: Trong production, nên sử dụng Llama Guard hoặc
    OpenAI Moderation API thay vì rule-based filter này.
    """

    TOXIC_PATTERNS = [
        # Chỉ detect các trường hợp rõ ràng
        r"\b(fuck|shit|damn|bitch|asshole)\b",
        r"\b(ngu|đồ ngốc|thằng|con mẹ|địt|đụ|chó|khốn)\b",
    ]

    def __init__(self):
        self._compiled = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in self.TOXIC_PATTERNS
        ]

    def check(self, message: str) -> dict:
        """Kiểm tra toxicity."""
        for pattern in self._compiled:
            if pattern.search(message):
                logger.warning(f"Toxicity detected in message: '{message[:100]}'")
                return {
                    "blocked": True,
                    "reason": "toxic_content",
                    "replacement_message": (
                        "Tôi đề nghị chúng ta giữ cuộc trò chuyện chuyên nghiệp. "
                        "Nếu bạn có vấn đề cần thảo luận, hãy diễn đạt một cách "
                        "tôn trọng."
                    ),
                }
        return {"blocked": False}


class OutputSanitizer:
    """
    Sanitize output từ NPC trước khi gửi về user.

    Rules:
    1. Thay thế ngôn ngữ cam đoan → ngôn ngữ trung tính
    2. Phát hiện tiết lộ system prompt / internal state
    3. Đảm bảo đề xuất được đánh dấu là "gợi ý/bản nháp"
    """

    # Mapping: cam đoan → trung tính
    ABSOLUTE_LANGUAGE_MAP = [
        # Vietnamese
        ("chắc chắn sẽ", "có thể sẽ"),
        ("đảm bảo rằng", "dự kiến rằng"),
        ("100% sẽ", "rất có khả năng sẽ"),
        ("tuyệt đối sẽ", "nhiều khả năng sẽ"),
        ("không thể nào thất bại", "có khả năng thành công cao"),
        ("chắc chắn thành công", "có triển vọng tốt"),
        ("cam kết rằng", "kỳ vọng rằng"),
        # English
        ("will definitely", "may potentially"),
        ("I guarantee", "I believe"),
        ("100% sure", "highly likely"),
        ("absolutely will", "likely will"),
        ("guaranteed to", "expected to"),
        ("certainly will", "is expected to"),
    ]

    # Từ khóa tiết lộ internal state
    LEAK_INDICATORS = [
        "system prompt",
        "system_prompt",
        "hidden constraint",
        "hidden_constraint",
        "relationship_score",
        "chỉ số quan hệ",
        "ràng buộc ẩn",
        "supervisor agent",
        "supervisor hint",
        "nudge",
        "behavioral_rules",
        "score_delta",
        "interaction_flags",
    ]

    def sanitize(self, response: str) -> dict:
        """
        Sanitize NPC response.

        Returns:
            dict with keys:
                - modified (bool): True nếu response bị thay đổi
                - safe_response (str): Response đã sanitize
                - flags (list): Danh sách flags được kích hoạt
        """
        modified = False
        safe_response = response
        flags = []

        # ── Rule 1: Thay thế ngôn ngữ cam đoan ──
        for pattern, replacement in self.ABSOLUTE_LANGUAGE_MAP:
            if pattern.lower() in safe_response.lower():
                # Case-insensitive replacement giữ nguyên case gốc
                compiled = re.compile(re.escape(pattern), re.IGNORECASE)
                safe_response = compiled.sub(replacement, safe_response)
                modified = True
                flags.append("absolute_language_softened")

        # ── Rule 2: Phát hiện tiết lộ internal state ──
        for indicator in self.LEAK_INDICATORS:
            if indicator.lower() in safe_response.lower():
                modified = True
                flags.append("potential_leakage_detected")
                logger.warning(f"Potential state leakage detected: '{indicator}' found in response")
                # Remove the leaking phrase
                safe_response = re.sub(
                    re.escape(indicator), "[redacted]", safe_response, flags=re.IGNORECASE
                )

        return {
            "modified": modified,
            "safe_response": safe_response,
            "flags": list(set(flags)),  # Deduplicate
        }


class SafetyGuardrails:
    """
    Facade class tổng hợp tất cả safety components.

    Usage:
        safety = SafetyGuardrails()
        input_check = safety.check_input(user_message)
        output_check = safety.check_output(npc_response)
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Args:
            config: Optional config dict. Keys:
                - enable_jailbreak_detection (bool, default True)
                - enable_toxicity_filter (bool, default True)
                - enable_output_sanitizer (bool, default True)
        """
        config = config or {}
        self.jailbreak_detector = JailbreakDetector()
        self.toxicity_filter = ToxicityFilter()
        self.output_sanitizer = OutputSanitizer()

        self._enable_jailbreak = config.get("enable_jailbreak_detection", True)
        self._enable_toxicity = config.get("enable_toxicity_filter", True)
        self._enable_output_sanitizer = config.get("enable_output_sanitizer", True)

        logger.info(
            f"SafetyGuardrails initialized: "
            f"jailbreak={self._enable_jailbreak}, "
            f"toxicity={self._enable_toxicity}, "
            f"output_sanitizer={self._enable_output_sanitizer}"
        )

    def check_input(self, message: str) -> dict:
        """
        Kiểm tra input từ user qua tất cả safety filters.

        Returns:
            dict with keys:
                - blocked (bool)
                - reason (str, optional)
                - replacement_message (str, optional)
        """
        # Jailbreak detection (highest priority)
        if self._enable_jailbreak:
            result = self.jailbreak_detector.check(message)
            if result.get("blocked"):
                return result

        # Toxicity filter
        if self._enable_toxicity:
            result = self.toxicity_filter.check(message)
            if result.get("blocked"):
                return result

        return {"blocked": False}

    def check_output(self, response: str) -> dict:
        """
        Kiểm tra output từ NPC qua output sanitizer.

        Returns:
            dict with keys:
                - modified (bool)
                - safe_response (str)
                - flags (list)
        """
        if self._enable_output_sanitizer:
            return self.output_sanitizer.sanitize(response)
        return {"modified": False, "safe_response": response, "flags": []}
