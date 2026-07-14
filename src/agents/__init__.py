"""
AI Co-worker Simulation Engine — Agents Package
Chứa các NPC Agent classes kế thừa từ BaseNPCAgent.
"""

from src.agents.base_agent import BaseNPCAgent, NPCState, NPCResponse
from src.agents.ceo_agent import CEOAgent
from src.agents.chro_agent import CHROAgent
from src.agents.regional_manager import RegionalManagerAgent

__all__ = [
    "BaseNPCAgent",
    "NPCState",
    "NPCResponse",
    "CEOAgent",
    "CHROAgent",
    "RegionalManagerAgent",
]
