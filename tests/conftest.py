# tests/conftest.py
import pytest
import requests
import pymysql  # 接入 MySQL 驱动
from config import settings as app_config

@pytest.fixture(scope="session")
def auth_session():
    """
    全局鉴权夹具：自动登录并维持 Session。
    """
    print("\n[Fixture启动] 正在进行全局登录并获取 Token...")
    session = requests.Session()
    login_url = f"{app_config.BASE_URL}/api/v1/login"
    
    try:
        resp = session.post(login_url, params={"username": "admin", "password": "123456"}, timeout=3)
        token = resp.json().get("token")
        if not token:
            pytest.fail("致命错误：无法获取 Token，鉴权失败！")
            
        session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"[Fixture启动] Token 注入成功 (截断显示): {token[:10]}...")
    except Exception as e:
        pytest.fail(f"登录接口请求异常，请检查 Mock 服务是否启动: {str(e)}")
        
    yield session
    
    print("\n[Fixture结束] 测试执行完毕，销毁全局 HTTP Session。")
    session.close()


# 1：建立一个贯穿全局的数据库连接
@pytest.fixture(scope="session")
def db_connection():
    """
    全局数据库连接夹具 (Session级别)：
    在所有测试开始前建立一次连接，所有测试结束后断开，避免频繁消耗数据库连接数。
    """
    print("\n[DB连接] 正在连接 Docker 测试数据库...")
    # 这里直接连接我们刚在 docker-compose 中配置的账号密码
    # 真实项目中，这些敏感信息也应提取到 config.py 或环境变量中
    connection = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='qa_user',
        password='qa_pass',
        database='automation_shop',
        charset='utf8mb4',
        # 【配置】让查询结果返回字典而不是元组，极大地简化了测试断言！
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True  # 关闭自动提交，我们在代码里手动 commit 确保安全
    )
    yield connection
    
    print("\n[DB连接] 所有测试结束，断开数据库连接。")
    connection.close()


#  2：优雅的数据清理闭环
@pytest.fixture(scope="function")
def cleanup_order_db(db_connection):
    """
    订单业务的专属后注意这里置清理夹具。
    db_connection，Pytest 会自动把上面建好的连接传进来。
    """
    # yield 前的 Setup，什么都不做，直接把控制权交给测试用例
    yield 
    
    # yield 后的 Teardown：测试用例跑完（无论成功失败）必然执行的代码
    print("\n[数据清理] 开始执行订单表脏数据清理...")
    try:
        with db_connection.cursor() as cursor:
            # 专业的做法是：只清理特定特征的测试数据，例如订单号带有 "QA_AUTO_" 前缀的
            sql = "DELETE FROM orders WHERE order_no LIKE %s"
            cursor.execute(sql, ('QA_AUTO_%',))
            deleted_rows = cursor.rowcount
            
        # 必须显式提交事务
        db_connection.commit()
        print(f"[数据清理] 完毕，安全清理了 {deleted_rows} 条以 QA_AUTO_ 开头的垃圾订单。")
        
    except Exception as e:
        db_connection.rollback()
        print(f"[数据清理异常] 回滚事务: {str(e)}")

import os
from ai_agent.failure_analyzer import LangChainFailureAgent

# 实例化 LangChain Agent
diagnostic_agent = LangChainFailureAgent()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Pytest 钩子函数：在每个测试用例运行结束后触发
    """
    # 获取测试执行结果
    outcome = yield
    report = outcome.get_result()

    # 核心逻辑：仅在测试用例真实执行阶段（call）且结果为失败（failed）时触发 AI
    if report.when == "call" and report.failed:
        test_name = item.nodeid
        # 提取报错堆栈
        error_trace = str(call.excinfo.value) if call.excinfo else report.longreprtext
        
        print(f"\n\n[LangChain Agent 介入] 检测到测试用例失败: {test_name}，正在进行智能归因...")
        
        # 尝试抓取最近的 server.log 尾部 30 行辅助分析 (如果有的话)
        server_logs = ""
        try:
            if os.path.exists("server.log"):
                with open("server.log", "r", encoding="utf-8") as f:
                    server_logs = "".join(f.readlines()[-30:])
        except Exception:
            pass

        # 触发大模型诊断
        analysis_result = diagnostic_agent.analyze(
            test_name=test_name,
            error_trace=error_trace,
            server_logs=server_logs
        )
        
        # 将大模型的分析结果直接打印到控制台
        print("\n================ AI 诊断报告 ================")
        print(analysis_result)
        print("================================================\n")