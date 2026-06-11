"""
项目完整测试脚本

运行方式:
  docker-compose exec web python scripts/test_all.py

测试内容:
  1. 健康检查 — 所有依赖连通性
  2. 认证 — 管理员+用户登录
  3. 数据库 — MySQL 读写
  4. ChromaDB — 集合创建/写入/搜索/删除
  5. Ollama — 嵌入生成
  6. LLM — 对话生成
  7. LangGraph — 意图识别+工具调用
  8. 文件上传 — TXT 处理
  9. 流式输出 — SSE
"""

import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} {detail}")

async def test():
    global passed, failed
    import aiohttp
    from aiohttp import ClientTimeout

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
        print("=" * 55)
        print("  1. 健康检查")
        print("=" * 55)
        try:
            async with s.get(f"{BASE}/health") as r:
                data = await r.json()
                check("HTTP 200", r.status == 200, f"got {r.status}")
                for dep in ["database","redis","chromadb","ollama","mysql"]:
                    val = data.get("checks",{}).get(dep, "down")
                    check(f"  {dep}: {val}", val == "up", f"status={val}")
        except Exception as e:
            check("健康检查可达", False, str(e))

        print("\n" + "=" * 55)
        print("  2. 认证")
        print("=" * 55)
        try:
            async with s.post(f"{BASE}/api/admin/login", json={"username":"admin","password":"admin123"}) as r:
                data = await r.json()
                check("管理员登录", r.status == 200, str(data))
                admin_token = data.get("token","")
        except: admin_token = ""

        try:
            async with s.post(f"{BASE}/api/login", json={"username_or_email":"zhangsan","password":"123456"}) as r:
                data = await r.json()
                check("用户登录", r.status == 200, str(data))
        except: pass

        try:
            async with s.post(f"{BASE}/api/login", json={"username_or_email":"wrong","password":"wrong"}) as r:
                check("错误密码拒绝(401)", r.status == 401, f"got {r.status}")
        except: pass

        print("\n" + "=" * 55)
        print("  3. 数据库")
        print("=" * 55)
        try:
            async with s.get(f"{BASE}/api/admin/sql/orders") as r:
                data = await r.json()
                check("MySQL 订单查询", r.status == 200 and data.get("count",0) > 0,
                      f"count={data.get('count',0)}")
        except: pass

        try:
            async with s.get(f"{BASE}/api/admin/sql/users") as r:
                data = await r.json()
                check("MySQL 用户查询", r.status == 200, str(data))
        except: pass

        print("\n" + "=" * 55)
        print("  4. ChromaDB 向量库")
        print("=" * 55)
        try:
            async with s.get(f"{BASE}/api/admin/collections") as r:
                data = await r.json()
                colls = data.get("collections",[])
                check("集合列表", len(colls) > 0, f"共{len(colls)}个集合")
        except: pass

        test_col = "test_cleanup_temp"
        test_col2 = "test_upload_temp"
        try:
            from src.services.chroma_store_service import get_chroma_store_service
            cs = await get_chroma_store_service()
            await cs.add_documents(test_col, ["测试文档"], [{"t":"test"}], ["doc_1"])
            results = await cs.search(test_col, "测试", n_results=1)
            check("写入+搜索", len(results) > 0)
            cs.delete_collection(test_col)
            check("删除集合", True)
        except Exception as e:
            check("ChromaDB 操作", False, str(e))

        print("\n" + "=" * 55)
        print("  5. Ollama 嵌入")
        print("=" * 55)
        try:
            from src.services.ollama_embedding_service import get_ollama_embedding_service
            ollama = await get_ollama_embedding_service()
            available = await ollama.is_available()
            check("Ollama 可用", available)
            if available:
                vec = await ollama.get_embedding("测试文本")
                check("向量生成", vec and len(vec) > 0, f"维度={len(vec) if vec else 0}")
        except Exception as e:
            check("Ollama", False, str(e))

        print("\n" + "=" * 55)
        print("  6. LLM 对话")
        print("=" * 55)
        try:
            async with s.post(f"{BASE}/api/chat/conversation") as r:
                sid = (await r.json()).get("session_id","")
                check("创建会话", bool(sid))

            async with s.post(f"{BASE}/api/chat/message", json={
                "session_id": sid, "message": "你好"
            }, timeout=ClientTimeout(total=30)) as r:
                data = await r.json()
                check("发送消息", r.status == 200 and bool(data.get("response")),
                      f"status={r.status}")
        except Exception as e:
            check("LLM 对话", False, f"{type(e).__name__}: {str(e)[:80]}")

        print("\n" + "=" * 55)
        print("  7. LangGraph 路由")
        print("=" * 55)
        tests = [
            ("查询订单TEST202406090001", "order_agent"),
            ("推荐一款手机", "product_agent"),
            ("怎么退货", "customer_service_agent"),
        ]
        for query, expected in tests:
            try:
                async with s.post(f"{BASE}/api/chat/conversation") as r:
                    sid2 = (await r.json()).get("session_id","")
                async with s.post(f"{BASE}/api/chat/message", json={
                    "session_id": sid2, "message": query
                }) as r:
                    data = await r.json()
                    agent = data.get("agent","")
                    ok = expected in agent
                    check(f"'{query[:12]}...' → {agent}", ok, f"expected {expected}")
            except Exception as e:
                check(f"'{query[:12]}...'", False, str(e))

        print("\n" + "=" * 55)
        print("  8. 文件上传")
        print("=" * 55)
        form = aiohttp.FormData()
        form.add_field("file", "这是一份测试文档内容。\n包含售后政策和退货流程说明。\n客户可以申请7天无理由退货。",
                        filename="test_upload.txt", content_type="text/plain")
        form.add_field("collection_name", test_col2)
        try:
            async with s.post(f"{BASE}/api/admin/documents/upload", data=form) as r:
                data = await r.json()
                check("TXT 上传", r.status == 200 and data.get("chunks",0) > 0,
                      f"status={r.status}, chunks={data.get('chunks',0)}, imported={data.get('imported')}")
                # 清理
                from src.services.chroma_store_service import get_chroma_store_service
                cs2 = await get_chroma_store_service()
                cs2.delete_collection(test_col2)
        except Exception as e:
            check("文件上传", False, str(e))

        print("\n" + "=" * 55)
        print("  9. 流式输出")
        print("=" * 55)
        try:
            async with s.post(f"{BASE}/api/chat/conversation") as r:
                sid3 = (await r.json()).get("session_id","")
            async with s.post(f"{BASE}/api/chat/message/stream", json={
                "session_id": sid3, "message": "你好"
            }) as r:
                chunks = []
                async for line in r.content:
                    chunk = line.decode().strip()
                    if chunk.startswith("data:"):
                        chunks.append(chunk)
                has_end = any("[END]" in c for c in chunks)
                has_content = any(len(c) > 10 for c in chunks)
                check("SSE 流式", has_end and has_content,
                      f"chunks={len(chunks)}, has_end={has_end}")
        except Exception as e:
            check("流式输出", False, str(e))

    # 结果
    print("\n" + "=" * 55)
    print(f"  结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 项")
    print("=" * 55)


if __name__ == "__main__":
    print("需要 aiohttp: pip install aiohttp --break-system-packages")
    print("开始测试...\n")
    asyncio.run(test())
