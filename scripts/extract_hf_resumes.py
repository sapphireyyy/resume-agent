"""
从 HuggingFace opensporks/resumes 提取 30 份 IT 类简历
配对 AI 应用开发 JD，标注 pass/pending/reject
"""
import json, os, random
import pandas as pd

# 读取 parquet
df = pd.read_parquet("real_data/hf/resumes.parquet")
print(f"总数据: {len(df)} 条")
print(f"列: {list(df.columns)}")

# IT 相关分类
it_categories = ["INFORMATION-TECHNOLOGY", "ENGINEERING", "CONSULTANT"]
it_df = df[df["Category"].isin(it_categories)]
print(f"IT 类: {len(it_df)} 条")

# 随机挑 30 条
random.seed(42)
sampled = it_df.sample(n=min(30, len(it_df)), random_state=42)

# ===== JD 定义 =====
JD_AI_APP = """AI 应用开发工程师
岗位要求：
1. 熟练使用 Python，熟悉 FastAPI/Django 等 Web 框架
2. 了解 LangChain/LangGraph 等 AI 应用框架
3. 具备数据库设计能力（MySQL/MongoDB/向量数据库）
4. 了解 Docker 容器化部署
5. 有完整的 AI 项目经验（RAG/Agent/ChatBot 等）
6. 良好的工程习惯：Git 版本管理、API 设计、异常处理"""

JD_BACKEND = """Python 后端开发工程师
岗位要求：
1. 精通 Python，熟练 FastAPI 或 Django 框架
2. 熟练 MySQL 数据库设计与优化
3. 熟悉 Redis 缓存、消息队列（RabbitMQ/Kafka）
4. 掌握 Docker 和云服务部署
5. 有微服务架构经验
6. 了解 CI/CD 流程"""

# 标注规则（更宽松，覆盖真实简历的多样技能写法）
def label_resume(resume_text, category):
    text = resume_text.lower()
    # AI/工程相关关键词（扩大匹配范围）
    ai_kws = ["python", "fastapi", "django", "flask", "sql", "postgresql", "mongodb", "nosql",
              "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "cloud",
              "git", "rest api", "api", "microservice", "backend", "full stack", "full-stack",
              "machine learning", "ai", "data science", "deep learning", "nlp", "llm",
              "java", "spring", "react", "node", "typescript", "javascript",
              "linux", "ci/cd", "jenkins", "devops", "agile", "scrum"]
    matches = sum(1 for kw in ai_kws if kw in text)
    
    # 真实简历标注策略：
    # pass: 有丰富软件工程经验（>=6 个工程关键词）
    # pending: 有基本技术背景，但可能不够匹配（3-5 个）
    # reject: 纯 IT 支持/管理岗，开发技能弱（<3 个）
    if matches >= 6:
        return "pass"
    elif matches >= 3:
        return "pending"
    else:
        return "reject"

# 构建 Harness 数据集
harness_cases = []
for i, row in sampled.iterrows():
    resume = str(row["Resume_str"])[:3000]  # 截断
    label = label_resume(resume, row["Category"])
    
    harness_cases.append({
        "id": f"hf-{i:04d}",
        "category": row["Category"],
        "jd": JD_AI_APP if random.random() > 0.4 else JD_BACKEND,
        "resume": resume,
        "expected": label,
    })

# 统计分布
from collections import Counter
dist = Counter(c["expected"] for c in harness_cases)
print(f"\n标注分布: {dict(dist)}")
print(f"pass={dist['pass']}, pending={dist['pending']}, reject={dist['reject']}")

# 输出为 dataset.py 格式
output = f'''"""Harness 数据集 — 30 份真实简历（HuggingFace opensporks/resumes） + AI 应用 JD，自动标注"""
cases = [
'''
for c in harness_cases:
    resume_escaped = json.dumps(c["resume"], ensure_ascii=False)
    jd_escaped = json.dumps(c["jd"], ensure_ascii=False)
    output += f'    {{"id": "{c["id"]}", "jd": {jd_escaped}, "resume": {resume_escaped}, "expected": "{c["expected"]}"}},\n'
output += "]\n\n\ndef get_dataset():\n    return cases\n"

with open("real_data/harness_real.py", "w", encoding="utf-8") as f:
    f.write(output)
print(f"已生成 real_data/harness_real.py ({len(harness_cases)} 条)")

# 同时保存简历文本
os.makedirs("real_data/hf_resumes", exist_ok=True)
for c in harness_cases:
    label = c["expected"]
    filename = f"real_data/hf_resumes/{label}_{c['id']}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(c["resume"])

print("简历文本已保存到 real_data/hf_resumes/")
