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

# 3. 配置 API Key
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 启动
python backend/main.py
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
| `/health` | GET | 健康检查 |

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
