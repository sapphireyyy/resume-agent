"""
从 HuggingFace 提取 20 条真实简历，用真实 AI Engineering JD 标注
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

# 读取 HuggingFace 数据
df = pd.read_parquet("real_data/hf/resumes.parquet")
# 优先 IT+Engineering，不够再加 CONSULTANT
target_cats = ["INFORMATION-TECHNOLOGY", "ENGINEERING"]
it_df = df[df["Category"].isin(target_cats)]
print(f"HuggingFace 总: {len(df)}, IT/Eng: {len(it_df)}")

# 按 JD 关键词打分
JD_KWS = {
    # AI/Agent 核心（高权重）
    "ai": 3, "artificial intelligence": 3, "machine learning": 3, "deep learning": 2,
    "agent": 3, "llm": 3, "langchain": 3, "langgraph": 3, "rag": 3,
    "nlp": 2, "chatgpt": 2, "openai": 2, "copilot": 3, "automation": 2,
    "python": 2, "fastapi": 2, "django": 2,
    # 工程能力
    "docker": 2, "kubernetes": 2, "k8s": 2, "aws": 2, "cloud": 1,
    "ci/cd": 2, "jenkins": 1, "git": 1, "agile": 1, "devops": 2,
    "api": 1, "rest": 1, "microservice": 2, "backend": 2,
    "sql": 1, "mysql": 1, "mongodb": 1, "database": 1,
    "workflow": 2, "pipeline": 1, "orchestration": 2,
    "java": 1, "spring": 1, "react": 1, "node": 1, "typescript": 1,
    "full stack": 2, "full-stack": 2,
}

def score_resume(text):
    text_l = text.lower()
    total = 0
    for kw, weight in JD_KWS.items():
        if kw in text_l:
            total += weight
    return total

# 全部打分
all_scores = []
for i, row in it_df.iterrows():
    text = str(row["Resume_str"])
    score = score_resume(text)
    all_scores.append((score, text[:3000], row["ID"]))

all_scores.sort(key=lambda x: -x[0])

# 选前 7 高分 = pass, 中间 7 = pending, 后 6 = reject
top7 = all_scores[:7]
mid7 = all_scores[len(all_scores)//2 - 3 : len(all_scores)//2 + 4]
low6 = all_scores[-6:]

print(f"\n标注结果:")
print(f"pass (7): scores {[s[0] for s in top7]}")
print(f"pending (7): scores {[s[0] for s in mid7]}")
print(f"reject (6): scores {[s[0] for s in low6]}")

# 组装数据集
all_cases = []
for score, resume, hf_id in top7:
    all_cases.append({"id": hf_id, "jd": JD, "resume": resume, "expected": "pass"})
for score, resume, hf_id in mid7:
    all_cases.append({"id": hf_id, "jd": JD, "resume": resume, "expected": "pending"})
for score, resume, hf_id in low6:
    all_cases.append({"id": hf_id, "jd": JD, "resume": resume, "expected": "reject"})

random.shuffle(all_cases)  # 打乱顺序

# 输出
output = '"""Harness 评测数据集 — 20 条 HuggingFace 开源真实简历 + AI Engineering JD"""\n\n'
# JD 太长，引用方式
output += '# JD 定义\nJD = """' + JD + '"""\n\n'
output += "cases = [\n"
for c in all_cases:
    r = json.dumps(c["resume"], ensure_ascii=False)
    output += f'    {{"id": "{c["id"]}", "jd": JD, "resume": {r}, "expected": "{c["expected"]}"}},\n'
output += "]\n\n\ndef get_dataset():\n    return cases\n"

with open("harness/dataset.py", "w", encoding="utf-8") as f:
    f.write(output)

from collections import Counter
dist = Counter(c["expected"] for c in all_cases)
print(f"\n最终分布: {dict(dist)} -> 已写入 harness/dataset.py")
