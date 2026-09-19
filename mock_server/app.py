import os
import time
import random
import asyncio
import hashlib
import pymysql
import redis.asyncio as redis 
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

# ========================================================
# 1. 全局配置与监控基建
# ========================================================
app = FastAPI(
    title="QA 旗舰级多业务线中台 Mock Server",
    description="企业级测试基建：涵盖电商交易状态机、智能驾驶并发遥测、车联网核心控制、Redis分布式锁及MQ异步削峰",
    version="3.0.0"
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

if not os.path.exists("logs"):
    os.makedirs("logs")

logger.add("logs/server_{time:YYYY-MM-DD}.log", rotation="00:00", retention="7 days", level="INFO", encoding="utf-8")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    client_ip = request.client.host if request.client else "Unknown"
    logger.warning(f"[安全拦截 422] | 源IP: {client_ip} | 路径: {request.url.path} | 恶意Payload: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": "参数校验失败，非法请求已记录", "errors": exc.errors()}
    )

redis_client = redis.Redis(host='127.0.0.1', port=6379, password='qa_redis_pass', decode_responses=True)

# ========================================================
# 2. 数据库自愈与双业务线自动建表
# ========================================================
def get_db_connection():
    return pymysql.connect(
        host='127.0.0.1', port=3306, user='qa_user', password='qa_pass',
        database='automation_shop', cursorclass=pymysql.cursors.DictCursor
    )

@app.on_event("startup")
async def ensure_database_schema():
    print("[应用自愈] 正在强制初始化双业务线(电商+车联)数据库表结构...")
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    item_name VARCHAR(100) NOT NULL,
                    qty INT NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    vin VARCHAR(50) NOT NULL,
                    domain VARCHAR(20) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    risk_level VARCHAR(20) NOT NULL,
                    payload JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_commands (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    vin VARCHAR(50) NOT NULL,
                    command_type VARCHAR(50) NOT NULL,
                    params JSON,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bms_alerts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    vin VARCHAR(50) NOT NULL,
                    alert_level VARCHAR(20) NOT NULL,
                    highest_temp FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cabin_settings (
                    vin VARCHAR(50) PRIMARY KEY,
                    profile_data JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        conn.close()
        print("✅ [应用自愈] 所有业务线底层表结构初始化/自检成功！")
    except Exception as e:
        print(f"❌ [应用自愈] 建表失败，请检查数据库连接: {e}")

# ========================================================
# 3. 业务线 A：电商核心交易链路
# ========================================================
class OrderRequest(BaseModel):
    item_name: str = Field(..., min_length=1, description="商品名不能为空")
    qty: int = Field(..., gt=0, le=1000000, description="订单数量必须在1到100万之间")

@app.post("/api/v1/login", tags=["全局鉴权"])
def login(username: str = "admin", password: str = "123456"):
    if username == "admin" and password == "123456":
        return {"code": 200, "message": "success", "token": "mock_token_888"}
    raise HTTPException(status_code=401, detail="账号或密码错误")

def verify_token(authorization: str = Header(None)):
    if not authorization or authorization != "Bearer mock_token_888":
        raise HTTPException(status_code=401, detail="无效或缺失的 Token，禁止访问！")
    return authorization

@app.post("/api/v1/orders", tags=["业务线 A：核心交易链路"])
def create_order(order: OrderRequest, token: str = Depends(verify_token)):
    if order.qty <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于0")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO orders (item_name, qty, status) VALUES (%s, %s, %s)", (order.item_name, order.qty, "PENDING"))
            order_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return {"code": 200, "message": "success", "data": {"order_id": order_id, "item_name": order.item_name, "current_status": "PENDING"}}

@app.post("/api/v1/orders/{order_id}/pay", tags=["业务线 A：核心交易链路"])
def pay_order(order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
            row = cursor.fetchone()
            if not row: raise HTTPException(status_code=404, detail="订单不存在")
            if row['status'] == "PAID": raise HTTPException(status_code=409, detail="订单已支付")
            if row['status'] == "CANCELLED": raise HTTPException(status_code=409, detail="订单已取消")
            cursor.execute("UPDATE orders SET status='PAID' WHERE id=%s", (order_id,))
        conn.commit()
    finally:
        conn.close()
    return {"code": 0, "msg": "支付成功", "data": {"order_id": order_id, "status": "PAID"}}

@app.post("/api/v1/orders/{order_id}/cancel", tags=["业务线 A：核心交易链路"])
def cancel_order(order_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
            row = cursor.fetchone()
            if not row: raise HTTPException(status_code=404, detail="订单不存在")
            if row['status'] == "PAID": raise HTTPException(status_code=409, detail="已支付无法取消")
            if row['status'] == "CANCELLED": raise HTTPException(status_code=409, detail="订单已取消")
            cursor.execute("UPDATE orders SET status='CANCELLED' WHERE id=%s", (order_id,))
        conn.commit()
    finally:
        conn.close()
    return {"code": 0, "msg": "取消成功", "data": {"order_id": order_id, "status": "CANCELLED"}}

db_inventory = {"sku_1001": 10}
successful_orders = 0  

@app.post("/api/v1/seckill/{sku_id}", tags=["业务线 A：核心交易链路"])
async def seckill_item(sku_id: str):
    global successful_orders
    lock_key = f"lock:seckill:{sku_id}"
    async with redis_client.lock(lock_key, timeout=5):
        current_stock = db_inventory.get(sku_id, 0)
        if current_stock > 0:
            await asyncio.sleep(0.1) 
            db_inventory[sku_id] = current_stock - 1
            successful_orders += 1  
            return {"msg": "抢购成功！", "remain": db_inventory[sku_id]}
        return {"msg": "库存不足，抢购失败", "remain": 0}

@app.get("/api/v1/inventory/{sku_id}", tags=["业务线 A：核心交易链路"])
def get_inventory(sku_id: str):
    return {"remain_stock": db_inventory.get(sku_id, 0), "total_sold": successful_orders}

# ========================================================
# 4. 业务线 B：智能网联汽车核心控制域
# ========================================================
class SensorPayload(BaseModel):
    vehicle_id: str
    event_type: str
    timestamp: float
    sensor_data: dict

@app.post("/api/v1/adas/telemetry", tags=["业务线 B：ADAS 仿真遥测"])
async def upload_sensor_data(payload: SensorPayload):
    if payload.event_type in ["AEB_TRIGGER", "TAKEOVER"]:
        await redis_client.lpush("queue:adas_critical_events", payload.model_dump_json())
        return {"code": 200, "msg": "紧急事件上报成功", "received_at": time.time()}
    return {"code": 200, "msg": "常规遥测数据上报成功", "received_at": time.time()}

class AdasEvent(BaseModel):
    vin: str
    sensor_type: str
    event_type: str

class RemoteCommand(BaseModel):
    action: str
    target_temp: Optional[float] = None

class BmsTelemetry(BaseModel):
    soc: int = Field(..., ge=0, le=100)
    temp_max: float
    charging_status: bool

class CabinProfile(BaseModel):
    seat_position: str
    ac_temp: float
    ambient_light_color: str
    steering_wheel_heating: bool

class SentryEvent(BaseModel):
    threat_level: str
    camera_id: str
    video_url: str

class OtaStrategy(BaseModel):
    target_version: str
    rollout_percentage: int

@app.post("/api/v1/adas/events", tags=["业务线 B：ADAS 紧急落库"])
def report_adas_event(event: AdasEvent, authorization: str = Header(None)):
    """真实落库：记录紧急驾驶事件"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO vehicle_events (vin, domain, event_type, risk_level, payload) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (event.vin, "ADAS", event.event_type, "HIGH", event.model_dump_json()))
            event_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return {"code": 200, "message": "ADAS event recorded", "risk_level": "HIGH", "event_id": event_id}

@app.post("/api/v1/vehicles/{vin}/command", tags=["业务线 B：Remote Control 远程车控"])
def send_remote_command(vin: str, cmd: RemoteCommand, authorization: str = Header(None)):
    """真实落库：下发车控指令并记录状态流转"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO vehicle_commands (vin, command_type, params, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (vin, cmd.action, cmd.model_dump_json(), "PENDING"))
            cmd_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return {"code": 200, "message": f"Command {cmd.action} sent", "command_id": cmd_id}

@app.post("/api/v1/bms/{vin}/telemetry", tags=["业务线 B：BMS 电池热管理"])
def report_bms(vin: str, data: BmsTelemetry):
    """真实落库：根据电池温度阈值动态落库"""
    alert = "CRITICAL" if data.temp_max > 80 else "NORMAL"
    if alert == "CRITICAL":
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = "INSERT INTO bms_alerts (vin, alert_level, highest_temp) VALUES (%s, %s, %s)"
                cursor.execute(sql, (vin, alert, data.temp_max))
            conn.commit()
        finally:
            conn.close()
    return {"code": 200, "status": "processed", "alert_level": alert}

@app.put("/api/v1/cabin/{vin}/profile", tags=["业务线 B：Smart Cabin 智能座舱"])
def sync_cabin_profile(vin: str, profile: CabinProfile):
    """真实落库：座舱配置的 Upsert (存在则更新，不存在则插入)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO cabin_settings (vin, profile_data) 
                VALUES (%s, %s) 
                ON DUPLICATE KEY UPDATE profile_data = VALUES(profile_data)
            """
            cursor.execute(sql, (vin, profile.model_dump_json()))
        conn.commit()
    finally:
        conn.close()
    return {"code": 200, "message": "Cabin profile synced"}

@app.post("/api/v1/security/{vin}/sentry_event", tags=["业务线 B：Sentry 安防哨兵"])
def report_sentry_event(vin: str, event: SentryEvent):
    """真实落库：哨兵模式视频凭证与威胁记录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO vehicle_events (vin, domain, event_type, risk_level, payload) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (vin, "SENTRY", "ALARM_TRIGGERED", event.threat_level, event.model_dump_json()))
        conn.commit()
    finally:
        conn.close()
    return {"code": 200, "message": "Sentry event processed", "alert_sent": True}

@app.post("/api/v1/ota/{vin}/strategy", tags=["业务线 B：OTA 空中升级"])
def deploy_ota(vin: str, strategy: OtaStrategy):
    """真实落库：OTA 升级策略下发控制"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO vehicle_commands (vin, command_type, params, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (vin, "OTA_UPDATE", strategy.model_dump_json(), "PENDING"))
        conn.commit()
    finally:
        conn.close()
    return {"code": 200, "message": f"OTA strategy deployed for {vin}"}

# --- 智能座舱语音模型 ---
class VoiceCommand(BaseModel):
    query: str = Field(..., description="用户的自然语言指令")
    audio_source: str = "MIC_DRIVER"

@app.post("/api/v1/cabin/voice_assistant", tags=["业务线 B：Smart Cabin 智能座舱语音"])
def process_voice_command(cmd: VoiceCommand):
    """模拟车载大模型语音意图解析与响应 (内含一个刻意设计的 Bug)"""
    query = cmd.query
    
    # 这是一个典型的“大模型意图理解错误/幻觉”Bug 用于演示 RCA
    if "冷" in query or "温度低" in query:
        # 错误逻辑：用户说冷，系统反而把温度调得更低，甚至开了冷风！
        return {
            "code": 200, 
            "intent": "SET_AC_TEMP",
            "action": "DECREASE_TEMP",
            "tts_reply": "好的，已经为您将空调温度调至 18 度，风量最大。",
            "executed": True
        }
    elif "后备箱" in query:
        return {
            "code": 200, 
            "intent": "OPEN_TRUNK",
            "action": "OPEN_TRUNK",
            "tts_reply": "好的，后备箱已开启。",
            "executed": True
        }
    else:
        return {
            "code": 200, 
            "intent": "UNKNOWN",
            "action": "NONE",
            "tts_reply": "抱歉，NOMI 没听懂您的指令。",
            "executed": False
        }

# ========================================================
# 5. 高阶架构模拟：Webhook 与 MQ 异步消费
# ========================================================
WEBHOOK_SECRET = "super_secret_key_from_alipay"

@app.post("/api/v1/webhook/pay_callback", tags=["异步架构：Webhook"])
async def pay_callback(order_id: str, amount: float, signature: str):
    expected_sign_str = f"{order_id}|{amount}|{WEBHOOK_SECRET}"
    expected_signature = hashlib.md5(expected_sign_str.encode()).hexdigest()
    if signature != expected_signature: return {"code": 403, "msg": "非法回调签名"}
    await asyncio.sleep(0.5) 
    if not hasattr(app.state, 'webhook_orders'): app.state.webhook_orders = {}
    app.state.webhook_orders[order_id] = "PAID"
    return {"code": 200, "msg": "回调接收成功"}

@app.get("/api/v1/order/status/{order_id}", tags=["异步架构：Webhook"])
def check_order_status(order_id: str):
    webhook_orders = getattr(app.state, 'webhook_orders', {})
    return {"order_id": order_id, "status": webhook_orders.get(order_id, "PENDING")}

db_user_points = {"user_888": 0}
MQ_NAME = "queue:order_paid_events"

async def mq_consumer_worker():
    while True:
        try:
            message = await redis_client.brpop(MQ_NAME, timeout=1)
            if message:
                _, order_id = message
                await asyncio.sleep(0.5) 
                db_user_points["user_888"] = db_user_points.get("user_888", 0) + 100
        except Exception:
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(mq_consumer_worker())

@app.post("/api/v1/order/{order_id}/pay_and_notify", tags=["异步架构：MQ消息队列"])
async def pay_and_notify(order_id: str):
    await redis_client.lpush(MQ_NAME, order_id)
    return {"code": 200, "msg": "支付成功，积分将在后台异步发放"}

@app.get("/api/v1/user/points/{user_id}", tags=["异步架构：MQ消息队列"])
def get_user_points(user_id: str):
    return {"user_id": user_id, "points": db_user_points.get(user_id, 0)}

# ========================================================
# 6. QA 效能工具平台 (数据工厂)
# ========================================================
@app.post("/api/v1/tools/batch-orders", tags=["🛠️ 测开效能工具"])
def batch_create_orders(count: int = 1000):
    if count <= 0 or count > 100000: return {"error": "数量必须在 1 到 100,000 之间"}
    start_time = time.time()
    orders = [(f"批量测试商品_SKU{random.randint(1000, 9999)}", random.randint(1, 50), "PENDING") for _ in range(count)]
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO orders (item_name, qty, status) VALUES (%s, %s, %s)", orders)
        conn.commit()
    finally:
        conn.close()
    end_time = time.time()
    logger.info(f"✅ [性能工具] 成功批量灌入 {count} 条数据，耗时 {end_time - start_time:.3f} 秒")
    return {"message": "batch generation success", "inserted_count": count, "time_cost_seconds": round(end_time - start_time, 3)}

@app.post("/api/v1/tools/init-test-stock/{sku_id}/{qty}", tags=["🛠️ 测开效能工具"])
def init_test_stock(sku_id: str, qty: int):
    db_inventory[sku_id] = qty
    return {"msg": f"{sku_id} 库存已重置为 {qty}"}