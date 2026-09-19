import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv  # 新增导入

# 自动寻找项目根目录的 .env 文件，并将里面的密钥加载到内存中
load_dotenv()
class LangChainFailureAgent:
    def __init__(self):
        # 1. 密钥
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # 2. 强制写入环境变量，完美避开底层参数识别 Bug
        os.environ["OPENAI_API_KEY"] = self.api_key
        os.environ["OPENAI_API_BASE"] = "https://api.siliconflow.cn/v1"
        
        # 指定硅基流动上的免费强力模型
        self.model_name = "deepseek-ai/DeepSeek-V3"
        
        # 3. 实例化时，无需再传入 api_key 和 base_url，它会自动读取环境变量
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.1,
            max_retries=2
        )
        
        # 构建标准的 PromptTemplate (解耦提示词与业务代码)
        self.prompt_template = PromptTemplate(
            input_variables=["test_name", "error_trace", "server_logs"],
            template="""你是一名资深测试开发架构师。请根据以下信息进行 CI/CD 流水线的测试失败归因。

【失败测试用例】: {test_name}
【抛出异常堆栈】: {error_trace}
【服务端尾部日志】: {server_logs}

请输出 Markdown 格式的排查诊断报告：
1. 核心故障点总结
2. 深度根因推导（结合报错与业务逻辑）
3. 建议排查与修复步骤
"""
        )
        
        # 组装 LCEL (LangChain Expression Language) 工作流链
        self.chain = self.prompt_template | self.llm | StrOutputParser()

    def analyze(self, test_name: str, error_trace: str, server_logs: str = "无附加日志") -> str:
        """
        向大模型发起调用，返回解析后的字符串
        """
        try:
            # 通过 invoke 传入变量，触发 LangChain 执行
            result = self.chain.invoke({
                "test_name": test_name,
                "error_trace": error_trace,
                "server_logs": server_logs
            })
            return result
        except Exception as e:
            return f"LangChain Agent 调用异常: {str(e)}"

# ================= 测试专用代码 =================
if __name__ == "__main__":
    agent = LangChainFailureAgent()
    print("正在连接硅基流动大模型测试...")
    
    # 模拟一个失败场景传给大模型
    test_res = agent.analyze(
        test_name="test_order.py::test_full_order_lifecycle",
        error_trace="AssertionError: 预期 200，实际返回 500",
        server_logs="pymysql.err.OperationalError: (2003, 'Can't connect to MySQL server on 127.0.0.1')"
    )
    
    print("\n✅ 成功获取返回结果：\n")
    print(test_res)