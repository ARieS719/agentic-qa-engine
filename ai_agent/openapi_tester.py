import os
import json
import requests
import pymysql
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from dotenv import load_dotenv  # 新增导入

# 自动寻找项目根目录的 .env 文件，并将里面的密钥加载到内存中
load_dotenv()
# =====================================================================
# 基础设施 1：动态拉取实时 OpenAPI (Swagger)
# =====================================================================
def get_live_api_docs():
    try:
        resp = requests.get("http://127.0.0.1:8000/openapi.json")
        data = resp.json()
        return json.dumps({
            "endpoints": data.get("paths", {}),
            "schemas": data.get("components", {}).get("schemas", {})
        }, ensure_ascii=False)
    except Exception as e:
        return f"无法拉取 API 文档: {e}"

# =====================================================================
# 基础设施 2：通用执行工具
# =====================================================================
@tool
def send_dynamic_http_request(method: str, endpoint: str, json_payload: dict = None) -> str:
    """通用 HTTP 发射器，用于向系统任意接口发起真实请求。"""
    url = f"http://127.0.0.1:8000{endpoint}"
    headers = {"Authorization": "Bearer mock_token_888"}
    try:
        print(f"\n[🔧 HTTP 执行] {method.upper()} {url} | Payload: {json_payload}")
        if method.upper() == "POST":
            resp = requests.post(url, json=json_payload, headers=headers)
        elif method.upper() == "PUT":
            resp = requests.put(url, json=json_payload, headers=headers)
        else:
            resp = requests.get(url, headers=headers)
        return f"HTTP Status: {resp.status_code}, Body: {resp.text}"
    except Exception as e:
        return f"请求异常: {str(e)}"

@tool
def execute_readonly_sql(sql_query: str) -> str:
    """底层数据穿透器：仅允许执行 SELECT 语句进行数据状态断言。"""
    if not sql_query.strip().upper().startswith("SELECT"):
        return "安全拦截：仅允许执行 SELECT 查询。"
    try:
        print(f"\n[SQL 执行] {sql_query}")
        conn = pymysql.connect(
            host='127.0.0.1', port=3306, user='qa_user', password='qa_pass',
            database='automation_shop', cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            records = cursor.fetchall()
        conn.close()
        return f"数据库查询结果: {records}"
    except Exception as e:
        return f"SQL执行失败: {str(e)}"

# =====================================================================
# 核心架构：极简且强大的 Native Agent 循环
# =====================================================================
def run_production_qa_agent(intent: str):
    # API Key
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_API_BASE"] = "https://api.siliconflow.cn/v1"

    # 启用顶配大模型：DeepSeek-V3
    llm = ChatOpenAI(model="deepseek-ai/DeepSeek-V3", temperature=0.1)
    
    tools = [send_dynamic_http_request, execute_readonly_sql]
    tools_map = {tool.name: tool for tool in tools}
    
    llm_with_tools = llm.bind_tools(tools)
    api_schema = get_live_api_docs()

    # 高效 Prompt：强调根据意图中的表名去查库
    system_prompt = f"""你是一个高阶 AI 测开架构师。
系统 OpenAPI 规范：
{api_schema}

请自主完成测试：
1. 查阅 API 规范，发 HTTP 请求构造数据。
2. 解析响应，编写 SQL 查验底层数据库。
3. 输出最终中文测试报告。
注意：在生成 SQL 时，请严格根据人类测试意图中提示的表名进行查询。
"""

    messages = [
        HumanMessage(content=f"{system_prompt}\n\n人类测试意图：{intent}")
    ]

    print(f"\n[生产级测试任务下发]：{intent}")
    print("=" * 70)

    # Native ReAct 循环 (最多允许 6 步工具调用交互)
    for step in range(6):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # 如果没有调用工具，说明大模型已经完成了所有步骤，得出了最终结论
        if not response.tool_calls:
            print("\n[生产级最终测试报告]：\n")
            print(response.content)
            return

        # 执行 AI 要求调用的工具
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            print(f"[Agent 智慧调度] 调用: {tool_name}，参数: {tool_args}")

            selected_tool = tools_map.get(tool_name)
            tool_result = selected_tool.invoke(tool_args) if selected_tool else f"找不到工具 {tool_name}"
            
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))

if __name__ == "__main__":
    # =====================================================================
    # 测试指令下发区 (在此切换车联六大核心场景)
    # =====================================================================
    test_intent = (
    "发布一次紧急的 OTA 升级策略。针对 VIN 码 'OTA-TEST-V3'，目标版本号 'v3.2.1'，灰度推送比例 20%。"
    "调用成功后，编写 SQL 穿透至 `vehicle_commands` 表，验证 command_type 是否被正确记录为 'OTA_UPDATE'。"
)
    
    run_production_qa_agent(test_intent)