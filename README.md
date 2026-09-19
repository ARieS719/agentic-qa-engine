# 基于 Agent 的车联网全域测试与质量效能平台

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![Pytest](https://img.shields.io/badge/Pytest-8.0+-yellow.svg)
![LangChain](https://img.shields.io/badge/LangChain-AI-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)

## 📖 项目概览
本项目为面向**智能网联汽车（车联底层架构/智能座舱）**与**车生活生态（高并发交易）**量身打造的下一代 AI 质量效能平台。

平台深度融合 **Agent 智能体架构** 与 **DevOps 效能理念**，彻底打通了从底层海量车控数据造血、代码变更精准调度、环境防御性自愈，到座舱多模态大模型语义评测（LLM-as-a-Judge）的全链路质量闭环。旨在解决复杂微服务架构下自动化脚本维护成本高、回归测试耗时长、智能座舱算法评测难的核心业务痛点。

## 🏗️ 核心架构与工程亮点

### 1. 全域聚合网关与高仿真白盒靶场 (DevOps & Infra)
*   **全场景业务域覆盖**：全面模拟车联底层架构与车生活生态，攻克 6 大高频复杂业务链路：
    1. **BMS 电池高频遥测**：海量时序数据上报与 MQ 异步队列削峰处理机制。
    2. **并发车控指令下发**：基于 Redis 分布式锁解决高并发下的指令防重与时序冲突。
    3. **OTA 固件升级状态机**：模拟整车跨版本升级的全生命周期闭环流转。
    4. **ADAS 紧急事件上报**：高优安全告警链路的低延迟触发与幂等性校验。
    5. **智能座舱多模态交互**：覆盖自然语言指令的模糊意图解析与容错兜底。
    6. **车生活商城高并发交易**：极速积分秒杀场景下的底层库存防超卖断言。
*   **企业级基建演进**：全面引入 Docker 容器化编排与多环境配置，集成 Prometheus 探针实现吞吐量实时监控。
*   **应用层防御性自愈**：FastAPI 启动时自动建立动态映射并修复底层 MySQL 数据表结构，彻底摆脱云端流水线脏数据带来的环境阻断问题。

### 2. 基于 ReAct 的测试智能体引擎 (Smart Agent)
*   **零硬编码测试覆盖**：摒弃传统繁琐的手写数据构造（Data Builder）模式，基于 LangChain 与 DeepSeek-V3 引擎自研 ReAct 驱动的测试智能体。
*   **全栈闭环自主校验**：Agent 动态解析 OpenAPI 规范自主发起探测请求，并跨界调用数据库执行工具，穿透至 MySQL 底层完成核心状态断言，实现低代码全链路验证。

### 3. 座舱多模态语义评测与智能 RCA (LLM-as-a-Judge)
*   **突破传统脚本局限**：针对智能座舱高度口语化、模糊化的交互场景，引入大模型作为智能裁判进行语义级断言，解决传统正则匹配无法验证意图的痛点。
*   **全链路推理追踪**：深度集成 **LangSmith** 监控中台，精准捕获大模型推理延迟与 Token 成本损耗，实现评测效能量化。
*   **算法根因分析闭环**：精准拦截座舱“意图倒置”与“知识幻觉”缺陷，自动生成标准化初步缺陷研判报告（RCA），反哺算法团队持续调优。

### 4. CI/CD 流水线与代码变更自愈 (Smart CI/CD)
*   **Git 变更精准调度**：开发智能调度引擎，通过分析 Git Diff 变更轨迹，精准挑选并拉起受影响的 Pytest 测试集，告别全量盲目回归。
*   **断言脚本自动演进**：捕获由于研发代码结构变动导致的断言失败，由自愈模块自动重构并修复 Pytest 测试脚本。
*   **构建优化与跨平台适配**：引入 `docker compose --wait` 同步机制，彻底解决云端流水线数据库初始化竞态导致的崩溃难题；深度修复 Allure 插件依赖，完美适配企业级 Linux CI 运行环境。

## 🛠️ 核心技术栈
*   **后端驱动**: Python 3.11, FastAPI, Pydantic
*   **测试基建**: Pytest, Allure, Locust (压测), Hypothesis (模糊测试)
*   **AI 与大模型**: LangChain, DeepSeek-V3, LangSmith
*   **中间件与存储**: Redis (分布式锁), PyMySQL (状态校验)
*   **DevOps**: Docker, Docker Compose, GitHub Actions, Prometheus

## 🚀 快速启动指南

### 1. 环境准备 (Docker 化一键部署)
确保本地已安装 Docker Desktop。项目根目录下执行：
```bash
# 一键拉起 MySQL、Redis 基础设施，利用 wait 机制保障启动顺序
docker compose up -d --wait
