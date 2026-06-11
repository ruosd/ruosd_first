from typing import Dict, Type, Optional, List
from ..agents.base_agent import BaseAgent

class AgentManager:
    """
    Agent管理器 - 管理所有Agent的注册和生命周期
    
    功能：
    - 使用单例模式管理Agent实例
    - 支持动态注册和注销Agent
    - 提供Agent查询和获取接口
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.agents: Dict[str, BaseAgent] = {}
        return cls._instance
    
    def register_agent(self, agent: BaseAgent):
        """注册一个新的Agent"""
        self.agents[agent.agent_name] = agent
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """根据名称获取Agent"""
        return self.agents.get(agent_name)
    
    def list_agents(self) -> List[Dict[str, str]]:
        """列出所有注册的Agent信息"""
        return [agent.get_agent_info() for agent in self.agents.values()]
    
    def unregister_agent(self, agent_name: str):
        """注销指定的Agent"""
        if agent_name in self.agents:
            del self.agents[agent_name]
    
    def has_agent(self, agent_name: str) -> bool:
        """检查是否注册了指定Agent"""
        return agent_name in self.agents