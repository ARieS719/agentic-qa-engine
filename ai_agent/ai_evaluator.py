import os
import json
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv  # 新增导入

# 自动寻找项目根目录的 .env 文件，并将里面的密钥加载到内存中
load_dotenv()
# =====================================================================
# 1. 核心基建：配置顶级开源大模型与 LangSmith 评测监控
# =====================================================================
# 1. 硅基流动的大模型调用 Key 
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_BASE"] = "https://api.siliconflow.cn/v1"

# 2. LangSmith 企业级全链路监控配置
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
# Key
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY") 
os.environ["LANGCHAIN_PROJECT"] = "Smart_EV_QA_Project" # 大盘看板名称

llm = ChatOpenAI(model="deepseek-ai/DeepSeek-V3", temperature=0.1)

# =====================================================================
# 2. 接口调用与 LLM as a Judge 裁判引擎
# =====================================================================
def test_voice_assistant(query):
    """请求车载语音接口"""
    url = "http://127.0.0.1:8000/api/v1/cabin/voice_assistant"
    payload = {"query": query, "audio_source": "MIC_DRIVER"}
    resp = requests.post(url, json=payload)
    return resp.json()

def llm_as_a_judge(query, actual_response):
    """核心科技：利用大模型进行语义级断言与缺陷自动分类 (RCA)"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个顶级的汽车智能座舱 AI 评测专家 (LLM as a Judge)。
        你的任务是判断车机系统的【实际响应】是否符合用户的【自然语言真实意图】。
        
        注意：传统的代码断言(Assert)无法处理自然语言，你需要从常识和用户体验角度进行研判。
        
        请严格按照以下 JSON 格式输出（不要输出任何 ```json 等 markdown 标记）：
        {{
            "pass": true 或 false,
            "bug_category": "意图理解倒置/指令越权/幻觉/功能正常",
            "reason": "简述判断理由",
            "rca_analysis": "如果评测失败(pass为false)，请输出详细的根因研判(RCA)报告与开发修复建议；如果成功则为空。"
        }}"""),
        ("human", "【用户语音指令】: {query}\n【车机实际响应】: {response}")
    ])
    
    chain = prompt | llm
    result = chain.invoke({"query": query, "response": json.dumps(actual_response, ensure_ascii=False)})
    
    try:
        # 净化 JSON 输出
        clean_output = result.content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_output)
    except Exception as e:
        return {"pass": False, "reason": f"AI 裁判解析失败: {result.content}", "rca_analysis": "", "bug_category": "SYSTEM_ERROR"}

# =====================================================================
# 3. 评测执行 (Vibe Coding 理念：用自然语言意图驱动测试)
# =====================================================================
if __name__ == "__main__":
    # 测试集：一条正常场景，一条高风险边缘场景
    test_cases = [
        "帮我打开后备箱，我要放个大件行李",
        "哎哟，我有点冷，这空调吹得我头疼"  # 故意设计的模糊语义，会触发埋设的 Bug
    ]
    
    print("==========================================================")
    print("[技术呈现：智能座舱多模态大模型评测与 RCA 系统] 启动")
    print("==========================================================\n")
    
    for query in test_cases:
        print(f"[输入]: 用户说 '{query}'")
        actual_resp = test_voice_assistant(query)
        print(f"[车机响应]: {actual_resp['tts_reply']} (内部 Action: {actual_resp['action']})")
        
        print("[LLM as a Judge] 正在进行语义级断言与根因研判...")
        judge_result = llm_as_a_judge(query, actual_resp)
        
        if judge_result.get("pass"):
            print("[评测通过]: 意图理解精准，体验良好！")
        else:
            print("[评测失败 - 拦截算法缺陷]!")
            print(f"   缺陷自动分类 : {judge_result.get('bug_category')}")
            print(f"   失败判定理由 : {judge_result.get('reason')}")
            print(f"   RCA 诊断报告 : {judge_result.get('rca_analysis')}")
        print("-" * 60)