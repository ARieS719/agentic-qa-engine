# 智能网联多业务中台 AI 自动化测试基建

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![Pytest](https://img.shields.io/badge/Pytest-8.0+-yellow.svg)
![LangChain](https://img.shields.io/badge/LangChain-AI-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)

## 项目概览
本项目为面向**智能网联汽车（车联网/智能座舱）**与**高并发交易中台**量身打造的企业级 AI 自动化测试基础设施。
项目深度融合 **Agent 智能体架构** 与 **DevOps 效能理念**，全面实现了从底层高仿真数据造血、代码变更精准调度、用例异常自愈，到座舱多模态大模型语义评测的全生命周期测试闭环，显著降低大型微服务架构的回归耗时与用例维护成本。

## 核心架构与工程亮点

### 1. 高可用聚合网关与白盒测试靶场 (DevOps & Infra)
*   **业务域覆盖**：全面模拟车联网（BMS高频遥测、ADAS紧急事件、OTA状态机）与电商（高并发秒杀防超卖）核心场景。
*   **企业级架构升级**：全面引入 Docker 化与多环境配置，完成全链路工程化升级[cite: 1]。
*   **高并发与稳定性保障**：集成 Prometheus 监控探针与 MQ 异步队列削峰[cite: 1]，利用 Redis 分布式锁解决并发车控指令与交易防重冲突。
*   **防御性自愈机制**：实现应用层防御性自愈，FastAPI 启动时动态映射并自动修复底层 MySQL 数据表结构，摆脱环境依赖带来的测试阻断[cite: 1]。

### 2. 基于 ReAct 的接口测试智能体 (Smart Agent)
*   **零硬编码数据构造**：摒弃传统繁琐的手写数据构造（Data Builder）模式，基于 LangChain 与 DeepSeek 大模型自研 ReAct 测试智能体。
*   **全栈闭环校验**：Agent 可动态解析 OpenAPI 规范自主发起网络请求，并调用专属 Tool 穿透至底层数据库完成状态断言，大幅缩短接口测试用例编写周期。

### 3. 多模态语义评测与智能 RCA 引擎 (LLM-as-a-Judge)
*   **突破传统断言局限**：针对智能座舱自然语言交互（如模糊意图、情感化指令）场景，引入大模型作为智能裁判进行语义级断言。
*   **全链路推理追踪**：深度集成 **LangSmith** 监控平台，精准捕获 AI 推理延迟与 Token 消耗，量化评测成本。
*   **根因分析闭环**：当检测到算法缺陷（如“意图倒置”、“知识幻觉”）时，自动拦截失败用例并生成标准化初步缺陷研判报告（RCA），直接赋能算法团队调优。

### 4. CI/CD 流水线与智能调度提效 (Smart CI/CD)
*   **精准调度引擎**：利用大模型语义分析 Git Diff 变更轨迹，精准挑选并拉起受影响的 Pytest 测试集，避免全量回归。
*   **代码自愈演进**：捕获接口变动导致的断言失败，自动重构并修复 Pytest 测试脚本。
*   **构建优化**：引入 `docker compose --wait` 机制，彻底解决云端流水线数据库初始化竞态导致的服务启动失败问题[cite: 1]；修复 Allure 插件及跨平台依赖问题以完美适配 Linux CI 环境[cite: 1]。

## 核心技术栈
*   **后端驱动**: Python 3.10+, FastAPI, Pydantic
*   **测试基建**: Pytest, Allure, Locust (压测), Hypothesis (模糊测试)
*   **AI 与大模型**: LangChain, DeepSeek-V3, LangSmith
*   **中间件与存储**: Redis (分布式锁), PyMySQL (状态校验), MQ
*   **DevOps**: Docker, Docker Compose, GitHub Actions, Prometheus

## 快速启动指南

### 1. 环境准备 (Docker 化一键部署)
确保本地已安装 Docker Desktop。项目根目录下执行：
```bash
# 一键拉起 MySQL、Redis 基础设施，利用 wait 机制保障启动顺序
docker-compose up -d --wait