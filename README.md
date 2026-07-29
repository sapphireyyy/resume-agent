# resume-agent — ReAct Supervisor 多 Agent 简历筛选系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于 LangGraph 的 **ReAct Supervisor 多 Agent 协作系统**，自动化评估候选人与岗位的匹配度。Supervisor 采用观察→决策→调用的自主推理模式，非固定路由的并行轮询。


## 架构

```
用户上传简历 PDF 或文本
         │
    MinerU PDF 解析  (表格/多栏/图文混排)
         │
    Supervisor (ReAct Agent)
    ├─→ 观察当前状态
    ├─→ 决策：该调哪个 Worker
    └─→ 调用 → 收到回报 → 重新观察
         │
    ┌────┼────┬────────┐
    ▼    ▼    ▼        ▼
  Skill  Exp  Risk  GitHub
  Agent Agent Agent Enrich
  技能  经历  风险  开源
  匹配  评分  检测  贡献
    │    │    │    │
    └────┼────┼────┘
         ▼
    综合评分 + 面试建议

评估维度：技能匹配 30+ 关键词 · 项目深度 · 实习质量 · 跳槽/空窗/学历 · GitHub 活跃度

Harness 评测：10 条模拟高匹配简历 + 10 条 HuggingFace 真实简历 → 自动回归验证
```

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/eybeyb/resume-screener.git
cd resume-screener

# 2. 安装
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env
# MinerU 精准解析 API 需要在 .env 中配置 MINERU_API_TOKEN；请勿提交真实 Token。
# PDF 流程会调用 /api/v4/file-urls/batch，上传后轮询 /api/v4/extract-results/batch/{batch_id}。
# .env 必须放在项目根目录，启动时由 backend/main.py 自动加载
# 必填：填入 DEEPSEEK_API_KEY（供 deepseek-chat 使用）
# 可选：MYSQL_URL；不填则使用项目根目录的 screener.db（SQLite）
# 可选：GITHUB_TOKEN；仅 GitHub Enrich Skill 读取并用于 GitHub API 鉴权
# 可选：LOG_DIR；日志目录相对项目根目录解析，默认使用 logs；目录不可写时自动降级为控制台日志
# 可选：LLM_TIMEOUT_SECONDS=45；单次模型调用超时
# 可选：LLM_MAX_RETRIES=2、LLM_RETRY_BACKOFF_SECONDS=1；失败时最多重试 2 次并指数退避
# 可选：LLM_RATE_LIMIT_PER_MINUTE=30、LLM_MIN_INTERVAL_SECONDS=0.2；共享限流策略
# 可选：LLM_RATE_LIMIT_WAIT_SECONDS=10；令牌等待超时后返回 degraded/rate_limited，不伪造评分

# 4. 启动
python backend/main.py
# 浏览器打开 http://localhost:8000

# Docker Compose 启动
docker compose up --build
# 浏览器打开 http://localhost:8000

# 5. 或直接用前端
# 打开 frontend/index.html 输入 JD + 简历文本即可
```

## 项目结构

```
resume-screener/
├── screening_engine/          # 多 Agent 核心
│   ├── supervisor_graph.py    # ReAct Supervisor 编排
│   └── agents/
│       ├── skill_agent.py     # 技能匹配 Worker
│       ├── experience_agent.py # 经历评分 Worker
│       └── risk_agent.py      # 风险检测 Worker
├── skills/                    # 5 个可复用 Skill 模块
│   ├── skill_match/           # 30+ 技术关键词对比
│   ├── experience_score/      # LLM 评估项目/实习质量
│   ├── risk_check/            # 5 类红旗检测
│   ├── parse_resume/          # MinerU PDF 解析
│   └── github_enrich/         # GitHub API 数据增强
├── harness/                   # Harness 评测框架
│   ├── dataset.py             # 20 条标注数据 (HuggingFace)
│   ├── adapter.py             # Agent 适配器
│   └── evaluator.py           # 3 维自动评分
├── backend/                   # FastAPI 后端
│   └── main.py                # 6 个 API 端点
├── frontend/                  # 前端界面
│   └── index.html             # JD + 简历输入 + 结果展示
├── tests/                     # 19 项自动化测试
│   └── test_all.py
├── scripts/                   # 数据生成/处理工具
├── Dockerfile + docker-compose.yml
└── requirements.txt
```

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/screen/text` | POST | 文本简历 + JD 筛选 |
| `/api/screen/pdf` | POST | PDF 简历上传 + 自动解析 |
| `/api/screen/{task_id}` | GET | 查询任务状态与结果 |
| `/api/history` | GET | 历史记录（分页） |
| `/api/harness/run` | POST | 一键运行 Harness 评测 |
| `/health` | GET | 启动依赖检查（模型 Key、数据库、PDF 解析器） |

`/health` 在依赖未就绪时仍返回 `200`，但会返回 `status: "degraded"`、`ready: false` 和具体失败项，便于定位配置问题。

LLM 调用失败时，Worker 会记录 `timeout`、`rate_limited` 或 `failed` 状态；Supervisor 将最终结论降级为“待定”，并在 `result.details.reliability` 中保留失败 Worker、重试次数和当前策略。后台任务状态会返回 `degraded`，便于调用方区分“完成”与“需要人工复核”。

PDF 简历会保留完整文本，并按 `basics`、`skills`、`work`、`education`、`projects`、`certifications` 等章节传给 Parser；不再使用固定的 8000 字符截断。下游 Agent 只接收相关章节和结构化字段，避免重复发送整份简历。

## 测试

```bash
python tests/test_all.py
# 19 项全部通过
#   5 Skills 模块测试
#   3 Agent 懒加载测试
#   2 Supervisor 图测试
#   2 Harness 评测测试
#   5 Backend API 测试
```

## 技术栈

**AI / Agent**：LangGraph · LangChain · ReAct Agent · Supervisor Pattern
**后端**：FastAPI · Pydantic · BackgroundTasks · SSE
**工具**：MinerU · GitHub API · PyPDF2
**评测**：Harness Framework · HuggingFace Datasets
**部署**：Docker · Docker Compose · GitHub Actions

## 许可证

MIT
