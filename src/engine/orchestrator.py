"""
Simulation Orchestrator
"""
import logging
import asyncio
from typing import Optional

from src.agents.ceo_agent import CEOAgent
from src.agents.chro_agent import CHROAgent
from src.agents.regional_manager import RegionalManagerAgent
from src.engine.llm_client import LLMClient
from src.engine.memory_manager import MemoryManager
from src.engine.safety_guardrails import SafetyGuardrails
from src.engine.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)

# Mock Tool Executor for now
class MockToolExecutor:
    def get_schemas_for(self, allowed_tools):
        return []
    def execute(self, tool_name, args):
        return {"result": f"Executed {tool_name} with {args}"}

class SimulationOrchestrator:
    def __init__(self, config=None):
        config = config or {}
        self.llm_client = LLMClient(config.get("llm"))
        self.memory = MemoryManager(config.get("memory"))
        self.tools = MockToolExecutor()
        self.safety = SafetyGuardrails(config.get("safety"))
        self.supervisor = SupervisorAgent(config.get("supervisor"), self.memory)
        
        # Initialize agents
        self.agents = {
            "gucci_ceo": CEOAgent(self.llm_client, self.memory, self.tools, self.safety),
            "gucci_chro": CHROAgent(self.llm_client, self.memory, self.tools, self.safety),
            "regional_manager": RegionalManagerAgent(self.llm_client, self.memory, self.tools, self.safety),
        }
        logger.info("SimulationOrchestrator initialized with 3 agents.")
        
    async def handle_message(self, user_id: str, target_persona: str, message: str):
        agent = self.agents.get(target_persona)
        if not agent:
            from src.agents.base_agent import NPCResponse
            return NPCResponse(
                message="Không tìm thấy đồng nghiệp này trong hệ thống.",
                state_update={},
                safety_flags=["invalid_persona"]
            )
            
        # Get Supervisor hint (async but awaited here for simplicity in prototype)
        supervisor_hint = await self._get_supervisor_hint(user_id, target_persona)
        
        # Process message
        response = agent.process_message(user_id, message, supervisor_hint)
        
        # Async tasks
        asyncio.create_task(
            self.supervisor.record_turn(user_id, target_persona, message, response.message)
        )
        self._update_shared_context(user_id, target_persona, message, response)
        
        return response
        
    async def _get_supervisor_hint(self, user_id: str, persona_id: str) -> Optional[str]:
        decision = await self.supervisor.evaluate(user_id, persona_id)
        if decision and decision.action == "nudge":
            return decision.nudge_message
        return None
        
    def _update_shared_context(self, user_id, persona_id, message, response):
        self.memory.add_cross_npc_event(
            user_id=user_id,
            source_persona=persona_id,
            summary=f"User trao đổi với {persona_id}: {message[:50]}...",
            key_outcome=response.state_update
        )
