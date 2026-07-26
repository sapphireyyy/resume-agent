"""
生成 Harness 数据集：30 条 JD-简历配对，pass/pending/reject 各 10
来源：10 AI 模拟简历 + 20 HuggingFace 真实 IT 简历
"""
import json, os, random, pandas as pd

JD = """AI 应用开发工程师（实习/校招）
岗位要求：
1. 掌握 Python，熟悉 FastAPI 或 Flask 等后端框架
2. 了解 AI 应用开发框架（如 LangChain/LangGraph）
3. 有数据库基础（MySQL/MongoDB）
4. 掌握 Docker 容器化基础
5. 有独立项目开发经验
6. 良好的代码习惯（Git/注释/异常处理）"""

# ===== 10 条 pass（高匹配 AI 简历） =====
pass_resumes = [
    "精通 Python，独立完成 2 个 FastAPI 后端项目。熟练使用 LangGraph 搭建多 Agent 系统，掌握 Docker 容器化部署。GitHub 持续维护开源项目。熟悉 MySQL 与 MongoDB，有数据库设计经验。",
    "Python 3年，FastAPI 开发微服务经验。独立搭建 RAG 知识库问答系统，使用 LangChain 编排导入/查询工作流，Milvus 向量检索。Docker Compose 一键部署。Git 版本管理规范。",
    "熟练 Python + FastAPI，做过 Agent 工具调用项目（ReAct 模式）。MySQL 数据库设计，RESTful API 设计。Docker 容器化经验。项目代码在 GitHub 开源。",
    "Python 后端 2 年，FastAPI/Django 双框架熟悉。LangChain Agent 开发经验，LLM 应用实践。MongoDB + Redis 缓存方案。Docker 部署线上服务。GitHub 200+ star 项目。",
    "Python FastAPI 搭建知识库后端，LangGraph 工作流编排。Milvus/Neo4j 混合检索，四路并行召回。Docker 编排 4 个数据库服务。MongoDB 会话管理。项目已上线，日活 100+。",
    "熟练 Python，个人项目用 FastAPI + MySQL 搭建博客后端。正在学习 LangChain Agent 开发。Docker 日常使用。GitHub 持续提交 6 个月。LeetCode 刷了 100 题。",
    "Python 后端实习经验，FastAPI 开发 3 个 API 服务。了解 RAG 原理，做过简单的文档问答 Demo。MySQL 数据库基础扎实。Docker 部署过个人项目。",
    "精通 Python，擅长 FastAPI 异步编程。熟悉 LangChain 工具链，做过 ChatBot 项目。掌握 MySQL 索引优化。Docker 容器化运维经验。有技术博客分享项目心得。",
    "Python FastAPI 2 年经验，做过 AI 客服系统（RAG+LLM）。MySQL 分库分表设计。Docker+K8s 部署经验。GitHub 维护 3 个 AI 相关开源项目。",
    "Python 熟练，FastAPI REST API 开发。自研 Agent 框架项目经验。熟悉 MySQL/MongoDB 数据库。Docker 日常开发使用。代码风格规范，有 Code Review 习惯。",
]

# ===== 10 条 pending（中匹配） =====
pending_resumes = [
    "Python 初学者，用过 Flask 写简单网站。对 AI 应用有兴趣，看过 LangChain 教程但还没实践过。会用 Docker 跑别人写好的镜像。Git 基本操作。",
    "Java 后端 2 年，想转 AI 方向。学过 Python 基础语法，没做过实际 AI 项目。了解 Docker 概念，没用过 LangChain/FastAPI。MySQL 数据库使用熟练。",
    "数据科学背景，Python 熟练但偏向数据分析（Pandas/Sklearn）。没做过 Web 后端，不知道 FastAPI/Docker。有 API 调用的经验。",
    "前端 React 开发 3 年，JavaScript/TypeScript 精通。想转全栈，正在学 Python 和 FastAPI 基础。Docker 不熟。项目主要在前端。",
    "大学计算机专业大三，Python 课上项目（学生管理系统 CRUD）。对 AI 方向有兴趣但没做过实际项目。MySQL 基础，用过 Git 交作业。",
    "IT 运维 2 年，精通 Linux 和 Shell 脚本。会写简单的 Python 脚本做自动化。了解 Docker，没用过 AI 框架。MySQL 基础操作。",
    "Java 后端实习 1 年，Spring Boot + MySQL 开发经验。学过 Python 但没用过。对 LangChain/LangGraph 完全不了解。Docker 只听过没用过。",
    "嵌入式开发背景，C/C++ 熟练。Python 只写过简单脚本。对 AI 应用开发不了解，Docker 零经验。愿意学习新技术。",
    "商科毕业生，自学 Python 6 个月。做过爬虫和数据可视化小项目。对 AI 应用开发很感兴趣，看过 ChatGPT API 文档。Git Basic 水平。",
    "测试工程师 2 年，写过 Python 自动化测试脚本。没开发过 Web 后端。了解 AI 概念但没实践过。MySQL 查询熟练。",
]

# ===== 10 条 reject（低匹配） =====
reject_resumes = [
    "8 年销售管理经验，带领 15 人团队。精通 CRM 系统和 Excel 数据分析。无编程基础，不会 Python。想转行 IT 但对技术要求不了解。",
    "4 年行政助理经验。熟练使用 Office 办公软件。打字速度 80 字/分钟。无编程或技术背景。希望学习新技能但零基础。",
    "10 年餐饮管理经验，运营 3 家连锁店。优秀的管理和沟通能力。不会编程，不懂计算机技术。想转行但方向不明确。",
    "5 年市场营销经验，擅长社交媒体运营。会用 Photoshop 和视频剪辑。没有编程经验。对 AI 听说过但不了解。",
    "2 年会计经验，CPA 持证。精通 Excel 和财务软件。Python/AI/编程完全不会。简历无任何技术关键词。",
    "应届英文专业毕业生。英语八级，日语 N2。office 软件熟悉。没有编程或计算机相关经验。希望找 AI 相关工作但无基础。",
    "7 年物流运输经验。熟悉仓储管理和供应链流程。不会使用编程工具。无计算机技术背景。",
    "初级护士 3 年，有护理执照。病人护理经验丰富。电脑操作仅限医院系统。完全不会编程。",
    "15 年教师经验，教授高中物理。优秀的表达和教学能力。基本电脑操作水平。没有编程基础。",
    "零售店员 2 年。良好的客户服务技能。基础电脑使用能力。无编程或开发经验。",
]

# ===== 从 HF 补 pending 和 reject（如不足则用模拟数据） =====
df = pd.read_parquet("real_data/hf/resumes.parquet")
it_df = df[df["Category"].isin(["INFORMATION-TECHNOLOGY", "ENGINEERING", "CONSULTANT"])]
random.seed(99)

# 从 HF 选 10 个 pending（IT 类但技能偏弱）
hf_samples = it_df.sample(n=min(20, len(it_df)), random_state=42)
hf_resumes = [str(r)[:1000] for r in hf_samples["Resume_str"]]
# 取一些在 pending 区间的
pending_resumes = pending_resumes[:5] + hf_resumes[:5]  # 5 模拟 + 5 真实

# 更多的模拟
reject_resumes = reject_resumes[:5] + [
    "数据分析师 1 年，会用 Excel 和 SQL 做报表。Python 只写过简单脚本。没做过后端开发，不了解 AI 框架。",
    "UI/UX 设计师 3 年，精通 Figma 和 Sketch。不会编程，有基础 HTML/CSS 理解。想转开发但没基础。",
    "产品经理 4 年，管理过技术团队。懂需求但不写代码。了解 AI 趋势但技术实现不了解。",
    "客服代表 5 年。良好的沟通能力。电脑操作仅限于客服系统。无编程经验。",
    "仓库管理员 6 年。会使用 WMS 系统和基础 Excel。不会编程或开发。",
]

# 组装最终数据集
all_cases = []
for i, resume in enumerate(pass_resumes):
    all_cases.append({"id": f"pass-{i+1:02d}", "jd": JD, "resume": resume, "expected": "pass"})
for i, resume in enumerate(pending_resumes):
    all_cases.append({"id": f"pending-{i+1:02d}", "jd": JD, "resume": resume, "expected": "pending"})
for i, resume in enumerate(reject_resumes):
    all_cases.append({"id": f"reject-{i+1:02d}", "jd": JD, "resume": resume, "expected": "reject"})

print(f"总: {len(all_cases)} 条")
from collections import Counter
print(f"分布: {dict(Counter(c['expected'] for c in all_cases))}")

# 输出
output = '"""Harness 数据集 — 30 条 JD-简历配对（含 HuggingFace 真实数据 + AI 应用 JD）"""\n\n'
output += 'JD = """' + JD + '"""\n\n'
output += "cases = [\n"
for c in all_cases:
    r = json.dumps(c["resume"], ensure_ascii=False)
    output += f'    {{"id": "{c["id"]}", "jd": JD, "resume": {r}, "expected": "{c["expected"]}"}},\n'
output += "]\n\n\ndef get_dataset():\n    return cases\n"

with open("harness/dataset.py", "w", encoding="utf-8") as f:
    f.write(output)
print("已覆盖 harness/dataset.py")

# 也保存简历文本
os.makedirs("real_data/final", exist_ok=True)
for c in all_cases:
    with open(f"real_data/final/{c['expected']}_{c['id']}.txt", "w", encoding="utf-8") as f:
        f.write(c["resume"])
print("简历保存到 real_data/final/")
