#!/usr/bin/env python3
"""延迟测试脚本"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_api_latency():
    """测试API延迟"""
    print("=" * 60)
    print("API延迟测试")
    print("=" * 60)
    
    # 1. 测试健康检查
    print("\n1. 测试健康检查接口")
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/health")
        latency = (time.time() - start_time) * 1000
        print(f"   状态: {'✓ 成功' if response.status_code == 200 else '✗ 失败'}")
        print(f"   延迟: {latency:.2f}ms")
    except Exception as e:
        print(f"   状态: ✗ 失败")
        print(f"   错误: {str(e)}")
    
    # 2. 测试创建会话
    print("\n2. 测试创建会话接口")
    start_time = time.time()
    session_id = None
    try:
        response = requests.post(f"{BASE_URL}/api/chat/conversation")
        latency = (time.time() - start_time) * 1000
        if response.status_code == 200:
            data = response.json()
            session_id = data["session_id"]
            print(f"   状态: ✓ 成功")
            print(f"   延迟: {latency:.2f}ms")
            print(f"   Session ID: {session_id[:8]}...")
        else:
            print(f"   状态: ✗ 失败")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   状态: ✗ 失败")
        print(f"   错误: {str(e)}")
    
    # 3. 测试发送消息（普通模式）
    if session_id:
        print("\n3. 测试发送消息接口（普通模式）")
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json={
                    "session_id": session_id,
                    "message": "你好，请问客服工作时间是什么时候？"
                }
            )
            latency = (time.time() - start_time) * 1000
            if response.status_code == 200:
                data = response.json()
                print(f"   状态: ✓ 成功")
                print(f"   延迟: {latency:.2f}ms")
                print(f"   Agent: {data.get('agent', '未知')}")
                print(f"   回复长度: {len(data.get('response', ''))} 字符")
            else:
                print(f"   状态: ✗ 失败")
                print(f"   响应: {response.text}")
        except Exception as e:
            print(f"   状态: ✗ 失败")
            print(f"   错误: {str(e)}")
    
    # 4. 测试发送消息（流式模式）
    if session_id:
        print("\n4. 测试发送消息接口（流式模式）")
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat/message/stream",
                json={
                    "session_id": session_id,
                    "message": "请问支持哪些支付方式？"
                },
                stream=True
            )
            total_latency = 0
            chunk_count = 0
            full_response = ""
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[5:]
                            if data.startswith('[END]'):
                                break
                            full_response += data
                            chunk_count += 1
                
                total_latency = (time.time() - start_time) * 1000
                print(f"   状态: ✓ 成功")
                print(f"   延迟: {total_latency:.2f}ms")
                print(f"   接收块数: {chunk_count}")
                print(f"   回复长度: {len(full_response)} 字符")
            else:
                print(f"   状态: ✗ 失败")
                print(f"   响应: {response.text}")
        except Exception as e:
            print(f"   状态: ✗ 失败")
            print(f"   错误: {str(e)}")
    
    # 5. 测试获取系统信息
    print("\n5. 测试系统信息接口")
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/system/info")
        latency = (time.time() - start_time) * 1000
        if response.status_code == 200:
            data = response.json()
            print(f"   状态: ✓ 成功")
            print(f"   延迟: {latency:.2f}ms")
            print(f"   系统: {data.get('system', '未知')}")
            print(f"   模型: {data.get('model', '未知')}")
            print(f"   Agent数量: {len(data.get('agents', []))}")
        else:
            print(f"   状态: ✗ 失败")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   状态: ✗ 失败")
        print(f"   错误: {str(e)}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    # 等待服务启动
    import time
    time.sleep(2)
    test_api_latency()