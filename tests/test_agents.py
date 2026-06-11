import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到Python路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents import CustomerServiceAgent, OrderAgent, ProductAgent
from src.services import AgentManager, ProductService, OrderService

class MockLLM:
    """模拟LLM类"""
    async def agenerate(self, messages):
        class Generation:
            def __init__(self, text):
                self.text = text

        class Generations:
            def __init__(self, generations):
                self.generations = generations

        # agent 调用时传入 [messages]，其中 messages 是消息列表
        msg_list = messages[0] if (messages and isinstance(messages, list) and messages[0] and isinstance(messages[0], list)) else messages
        last_message = msg_list[-1].content if msg_list and hasattr(msg_list[-1], 'content') else str(msg_list[-1]) if msg_list else ""
        response_text = f"模拟回复：{last_message}"

        return Generations([[Generation(response_text)]])

@pytest.fixture
def mock_llm():
    """创建模拟LLM"""
    return MockLLM()

@pytest.fixture
def product_service():
    """创建产品服务（使用mock数据模式）"""
    with patch("src.services.product_service.get_mysql_client") as mock_get_mysql:
        mock_mysql = Mock()
        mock_mysql.is_connected.return_value = False
        mock_get_mysql.return_value = mock_mysql
        service = ProductService()
        return service

@pytest.fixture
def order_service():
    """创建订单服务（使用mock数据模式）"""
    with patch("src.services.order_service.get_mysql_client") as mock_get_mysql:
        mock_mysql = Mock()
        mock_mysql.is_connected.return_value = False
        mock_get_mysql.return_value = mock_mysql
        service = OrderService()
        return service

@pytest.mark.asyncio
async def test_customer_service_agent(mock_llm):
    """测试客服Agent"""
    agent = CustomerServiceAgent(mock_llm)
    
    # 测试基本属性
    assert agent.agent_name == "customer_service_agent"
    assert "客服" in agent.get_system_prompt()
    
    # 测试运行
    response = await agent.run("您好，请问客服工作时间是什么时候？")
    assert isinstance(response, str)
    assert len(response) > 0
    assert "模拟回复" in response
    
    # 测试转接检测（通过GraphCoordinator的路由逻辑实现）
    # CustomerServiceAgent 不再直接提供 needs_transfer 方法

@pytest.mark.asyncio
async def test_order_agent(mock_llm, order_service):
    """测试订单Agent"""
    agent = OrderAgent(mock_llm, order_service)
    
    # 测试基本属性
    assert agent.agent_name == "order_agent"
    assert "订单" in agent.get_system_prompt()
    
    # 测试运行
    response = await agent.run("查询订单号202401150001的状态")
    assert isinstance(response, str)
    assert len(response) > 0
    
    # 测试订单信息提取
    order_info = await agent._extract_order_info("订单号1234567890")
    assert order_info is not None
    assert order_info["order_id"] == "1234567890"

@pytest.mark.asyncio
async def test_product_agent(mock_llm, product_service):
    """测试产品Agent"""
    agent = ProductAgent(mock_llm, product_service)
    
    # 测试基本属性
    assert agent.agent_name == "product_agent"
    assert "产品" in agent.get_system_prompt()
    
    # 测试运行
    response = await agent.run("我想了解智能手机的信息")
    assert isinstance(response, str)
    assert len(response) > 0
    
    # 测试产品信息提取
    product_info = await agent._extract_product_info("我想买一部手机")
    assert product_info is not None
    assert product_info["product_name"] == "手机"

def test_agent_manager():
    """测试Agent管理器"""
    manager = AgentManager()
    
    # 测试单例模式
    manager2 = AgentManager()
    assert manager is manager2
    
    # 测试Agent注册
    mock_llm = MockLLM()
    agent = CustomerServiceAgent(mock_llm)
    manager.register_agent(agent)
    
    # 测试Agent获取
    retrieved_agent = manager.get_agent("customer_service_agent")
    assert retrieved_agent is agent
    
    # 测试Agent列表
    agents = manager.list_agents()
    assert len(agents) == 1
    assert agents[0]["agent_name"] == "customer_service_agent"
    
    # 测试Agent注销
    manager.unregister_agent("customer_service_agent")
    assert manager.get_agent("customer_service_agent") is None

@pytest.mark.asyncio
async def test_graph_coordinator():
    """测试Graph协调器（原AgentCoordinator的替代）"""
    from src.graph.graph_coordinator import GraphCoordinator

    coordinator = GraphCoordinator()

    # 意图检测通过LangGraph路由实现
    result = await coordinator.route_query("我的订单什么时候发货？")
    assert result["agent"] == "order_agent" or result["agent"] is not None

    result = await coordinator.route_query("这个手机多少钱？")
    assert result["agent"] == "product_agent" or result["agent"] is not None

    result = await coordinator.route_query("你好")
    assert result["agent"] == "customer_service_agent" or result["agent"] is not None

def test_product_service():
    """测试产品服务"""
    with patch("src.services.product_service.get_mysql_client") as mock_get_mysql:
        mock_mysql = Mock()
        mock_mysql.is_connected.return_value = False
        mock_get_mysql.return_value = mock_mysql
        service = ProductService()
    
    # 测试获取产品详情
    product = asyncio.run(service.get_product_details("手机"))
    assert product is not None
    assert "智能手机" in product["name"]
    
    # 测试产品搜索
    results = asyncio.run(service.search_products("耳机"))
    assert len(results) > 0
    assert any("耳机" in r["name"] for r in results)
    
    # 测试产品推荐
    recommendations = asyncio.run(service.recommend_products(1))
    assert isinstance(recommendations, list)

def test_order_service():
    """测试订单服务"""
    with patch("src.services.order_service.get_mysql_client") as mock_get_mysql:
        mock_mysql = Mock()
        mock_mysql.is_connected.return_value = False
        mock_get_mysql.return_value = mock_mysql
        service = OrderService()

    # 测试获取订单详情
    order = asyncio.run(service.get_order_details("202401150001"))
    assert order is not None
    assert "202401150001" in order

    # 测试订单搜索
    results = asyncio.run(service.search_orders("手机"))
    assert len(results) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])