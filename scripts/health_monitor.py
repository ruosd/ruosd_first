"""
系统健康监控 + 告警

原理:
  定期调用 /health 端点，发现任何依赖变为 "down" 时，通过 webhook 发送告警。
  可配置钉钉/企业微信/Slack webhook 地址。

使用方式:
  docker-compose exec web python scripts/health_monitor.py
  或作为 Celery 定时任务运行
"""

import os, sys, time, json, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEALTH_URL = os.getenv("HEALTH_URL", "http://127.0.0.1:8000/health")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))  # 秒
WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")          # 钉钉/企微/Slack webhook
COOLDOWN = 300  # 同一个告警 5 分钟内不重复发

last_alert = {}  # {dependency: timestamp}


def send_alert(dep: str, status: str):
    """发送告警"""
    global last_alert
    now = time.time()
    if dep in last_alert and now - last_alert[dep] < COOLDOWN:
        return  # 冷却中，不重复发送

    last_alert[dep] = now
    msg = f"⚠️ [{dep}] 状态异常: {status}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"

    print(msg)

    if WEBHOOK_URL:
        data = json.dumps({"msgtype": "text", "text": {"content": msg}}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(
                WEBHOOK_URL, data=data,
                headers={"Content-Type": "application/json"}
            ))
        except Exception as e:
            print(f"  告警发送失败: {e}")


def check():
    """单次健康检查"""
    try:
        resp = urllib.request.urlopen(HEALTH_URL, timeout=5)
        data = json.loads(resp.read())
        checks = data.get("checks", {})
        status = data.get("status", "unknown")

        if status == "healthy":
            return

        for dep, state in checks.items():
            if state == "down":
                send_alert(dep, state)

    except Exception as e:
        send_alert("system", f"健康检查失败: {e}")


if __name__ == "__main__":
    print(f"健康监控启动 (间隔 {CHECK_INTERVAL}s)")

    while True:
        check()
        time.sleep(CHECK_INTERVAL)
