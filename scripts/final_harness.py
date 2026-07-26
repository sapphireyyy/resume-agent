"""
最终 Harness：10 pass(模拟) + 5 pending(HF真实) + 5 reject(HF真实)，统一 AI Engineering JD
"""
import json, os, random, pandas as pd

JD = """职位详情
1、负责AI提效相关工作的设计、开发和落地，围绕组织效率提升、研发方式升级和AI-Native工作模式建设，推动关键项目形成可复用、可推广的实践;
2、负责AICoding方向的工程化落地，推进代码生成、测试辅助、代码评审、研发协同等能力进入真实研发流程，推动Harness Engineering等前沿实践沉淀为团队级方法论和工程标准;
3、负责AIAgent方向的探索与落地，推动OpenClaw等Agent框架在办公、研发、协同等场景中的实际应用，推进数字员工方案从Demo走向稳定运行;
4、负责相关能力的平台化与治理建设，明确协作机制、权限控制、风险治理、效果评估与可观测性要求，保障能力可用、可信、可规模化推广;
5、结合实际业务场景，持续优化AI能力接入方式、Workflow设计和系统稳定性，推动AI能力在真实环境中长期发挥价值。

职位要求
1、有AIEngineering、研发效能、工程平台、自动化工作流或相关方向的实践经验，能够独立推进功能落地与方案实现;
2、具备扎实的工程能力，有AICoding工程化实践经验优先;有AIAgent、自动化工作流、数字员工或企业级协同系统相关实践经验优先;
3、对AI前沿方向有深刻理解，尤其对AICoding、Agent、模型能力演进等方向保持持续关注，能够结合业务场景完成技术选型与落地实现;
4、具备良好的工程化思维，能够将快速变化的AI能力转化为稳定、可维护、可扩展的工程方案;
5、有较强的问题拆解与协同推进能力，能够在复杂场景下与产品、业务、平台、研发等角色高效协作;
6、对新技术保持好奇心和执行力，愿意持续学习并推动AI能力在组织中的真实落地。

加分项:
1、有Harness Engineering、Agent平台、企业级AI工作流、数字员工体系等相关实践经验;
2、有OpenClaw、Copilot类产品、Code Agent、自动化协同系统等实际落地经验;
3、持续关注并输出AI前沿趋势判断、实践总结或方法论沉淀。"""

# ===== 10 pass: 模拟高匹配简历 =====
pass_resumes = [
    "AI应用工程师 2年，精通 Python/FastAPI/LangGraph。独立搭建多 Agent 协作系统（Supervisor 模式），Harness 评测框架量化 Agent 质量。Docker/K8s 部署经验，推动 AI Coding 工具链落地。",
    "Python 3年，FastAPI 微服务 + LangChain Agent 开发。搭建 RAG 知识库 + RRF 自研融合算法，覆盖 4 路并行召回。推动 AI 代码评审流程，减少 Code Review 时间 60%。Docker Compose 编排 4 个数据库服务。",
    "AI 平台工程师，负责 Agent 框架选型与落地。设计 Supervisor 多 Agent 架构，集成 LangGraph 工作流引擎。推进 AI-Native 研发模式，建立 Agent 效果评估体系（准确率/延迟/覆盖率）。Python/FastAPI/Docker。",
    "精通 Python，独立完成 2 个 AI 应用项目。LangGraph Supervisor 多 Agent 系统，Harness 自动化评测框架（20+ 场景 × 4 维评分）。Docker 部署，CI/CD 门禁集成。MySQL/MongoDB 数据层设计。",
    "AI 后端开发，FastAPI + LangChain + Milvus。构建 RAG 检索系统，支持四路并行召回与 Reranker 重排序。推动 AICoding 工程化落地：代码生成 + 测试辅助 + Code Review 自动检测。Docker/K8s 运维。",
    "Python 后端 2.5 年，主导 AI 应用平台开发。设计 LangGraph Supervisor 多 Agent 架构，3 个 Worker Agent 协作。Harness 评测框架接入 CI 门禁。Agent 平台化治理：权限/风控/可观测性。",
    "全栈工程师，Python/FastAPI + React。做过 AI Agent 产品，从 Demo 到生产环境完整落地。建立 Agent 评估指标体系，量化质量与效率提升。Docker + K8s 部署，自动化 CI/CD。",
    "AI 应用开发，熟悉 LangChain/LangGraph 框架。独立完成多 Agent 协作系统（ReAct Supervisor），Skill 模块化设计（yaml 元数据 + @tool 注册）。推动 AI 辅助编码流程标准化。",
    "Python FastAPI 3 年，Agent 平台开发经验。设计 Harness Engineering 实践：自动化评测 + 回归测试 + 质量门禁。推动 AI Workflow 在企业落地，优化系统稳定性。Docker 容器化运维。",
    "AI 工程师，精通 Agent 框架（LangGraph/CrewAI）。搭建数字员工方案：Multi-Agent 协作 + Harness 评测 + Docker 部署。推动 Harness Engineering 方法论沉淀，输出技术文档与实践总结。",
]

# ===== 从 HF 取 pending + reject =====
df = pd.read_parquet("real_data/hf/resumes.parquet")
it_df = df[df["Category"].isin(["INFORMATION-TECHNOLOGY", "ENGINEERING", "CONSULTANT"])]

# 按匹配度排序，取中段和高段做 pending，低段做 reject
JD_KWS = {"ai":3,"machine learning":3,"agent":3,"llm":3,"python":2,"docker":2,"api":1,"sql":1,"java":1,"automation":2,"devops":2}
def score(text):
    return sum(w for k,w in JD_KWS.items() if k in text.lower())

all_scored = [(score(str(r["Resume_str"])), str(r["Resume_str"])[:3000], r["ID"])
              for _, r in it_df.iterrows()]
all_scored.sort(key=lambda x: -x[0])

# pending: 中等分数（5条）
pending = all_scored[len(all_scored)//3 : len(all_scored)//3 + 5]
# reject: 最低分（5条）
reject = all_scored[-5:]

print(f"pass(模拟): 10 | pending(HF): 5 | reject(HF): 5")
print(f"pending scores: {[s[0] for s in pending]}")
print(f"reject scores: {[s[0] for s in reject]}")

# 组装
cases = []
for i, r in enumerate(pass_resumes):
    cases.append({"id": f"pass-{i+1:02d}", "jd": JD, "resume": r, "expected": "pass"})
for s, r, hf_id in pending:
    cases.append({"id": hf_id, "jd": JD, "resume": r, "expected": "pending"})
for s, r, hf_id in reject:
    cases.append({"id": hf_id, "jd": JD, "resume": r, "expected": "reject"})
random.shuffle(cases)

# 写入
out = '"""Harness 评测 — 20 条 (10 模拟 pass + 10 HF真实 pending/reject) | AI Engineering JD"""\n\n'
out += 'JD = """' + JD + '"""\n\n'
out += "cases = [\n"
for c in cases:
    r = json.dumps(c["resume"], ensure_ascii=False)
    out += f'    {{"id": "{c["id"]}", "jd": JD, "resume": {r}, "expected": "{c["expected"]}"}},\n'
out += "]\n\n\ndef get_dataset():\n    return cases\n"

with open("harness/dataset.py", "w", encoding="utf-8") as f:
    f.write(out)

from collections import Counter
print(f"写入完成: {dict(Counter(c['expected'] for c in cases))}")
