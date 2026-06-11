#!/usr/bin/env python3
"""Agent转接功能测试脚本"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.settings import settings
from src.services.agent_manager import AgentManager
from src.services.agent_coordinator import AgentCoordinator
from langchain_community.chat_models import ChatOpenAI

async def test_agent_routing():
    """测试Agent路由功能"""
    print("=" * 70)
    print("Agent转接功能测试")
    print("=" * 70)
    
    # 初始化LLM
    print("\n初始化LLM...")
    llm = ChatOpenAI(
        model_name=settings.ALIYUN_MODEL_NAME,
        openai_api_key=settings.ALIYUN_API_KEY,
        openai_api_base=settings.ALIYUN_API_BASE,
        temperature=0.7,
        max_tokens=2048
    )
    print(f"✓ LLM初始化成功，使用模型: {settings.ALIYUN_MODEL_NAME}")
    
    # 初始化Agent管理器
    print("\n初始化Agent管理器...")
    from src.agents import CustomerServiceAgent, OrderAgent, ProductAgent
    from src.services import ProductService, OrderService
    
    agent_manager = AgentManager()
    
    # 注册Agent
    print("注册Agent...")
    product_service = ProductService()
    order_service = OrderService()
    
    agent_manager.register_agent(CustomerServiceAgent(llm))
    agent_manager.register_agent(OrderAgent(llm, order_service))
    agent_manager.register_agent(ProductAgent(llm, product_service))
    
    agents = agent_manager.list_agents()
    print(f"✓ 已注册 {len(agents)} 个Agent:")
    for agent in agents:
        print(f"  - {agent['agent_name']}")
    
    # 初始化协调器
    coordinator = AgentCoordinator()
    
    # 测试用例
    test_cases = [
        {
            "query": "你好，请问客服工作时间是什么时候？",
            "expected_agent": "customer_service_agent",
            "description": "通用问题，应该使用客服Agent"
        },
        {
            "query": "查询订单号202401150001的状态",
            "expected_agent": "order_agent",
            "description": "订单查询，应该使用订单Agent"
        },
        {
            "query": "请问iPhone手机的价格是多少？",
            "expected_agent": "product_agent",
            "description": "产品咨询，应该使用产品Agent"
        },
        {
            "query": "我的快递什么时候能到？",
            "expected_agent": "order_agent",
            "description": "物流查询，应该使用订单Agent"
        },
        {
            "query": "我要退货，怎么操作？",
            "expected_agent": "order_agent",
            "description": "退货咨询，应该使用订单Agent"
        }
    ]
    
    print("\n" + "=" * 70)
    print("开始路由测试")
    print("=" * 70)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n【测试 {i}】{test_case['description']}")
        print(f"查询: {test_case['query']}")
        print(f"期望Agent: {test_case['expected_agent']}")
        
        try:
            result = await coordinator.route_query(
                user_query=test_case['query'],
                conversation_history=None,
                current_agent=None
            )
            
            actual_agent = result['agent']
            response_preview = result['response'][:50] + "..." if len(result['response']) > 50 else result['response']
            
            print(f"实际Agent: {actual_agent}")
            print(f"响应预览: {response_preview}")
            
            if actual_agent == test_case['expected_agent']:
                print(f"✓ 测试通过！")
                success_count += 1
            else:
                print(f"✗ 测试失败！期望 {test_case['expected_agent']}，实际 {actual_agent}")
        except Exception as e:
            print(f"✗ 测试出错: {str(e)}")
    
    print("\n" + "=" * 70)
    print(f"测试完成: {success_count}/{total_count} 通过")
    print("=" * 70)
    
    if success_count == total_count:
        print("✓ 所有测试通过！Agent转接功能正常。")
    else:
        print(f"✗ 有 {total_count - success_count} 个测试失败。")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        result = asyncio.run(test_agent_routing())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n✗ 测试脚本执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)