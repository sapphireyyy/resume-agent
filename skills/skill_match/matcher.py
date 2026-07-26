"""
技能匹配 Skill — 简历技能 vs JD 要求，逐条对比打分
通过 @tool 装饰器注册给 Agent，硬规则 + LLM 辅助
"""
import json
from logger_config import setup_logger

logger = setup_logger("skills.skill_match")


class SkillMatcher:
    """JD-简历技能对比器"""

    TECH_KEYWORDS = [
        # Python 后端
        "python", "fastapi", "django", "flask", "sqlalchemy", "pydantic", "asyncio",
        # Java 生态
        "java", "spring", "spring boot", "spring cloud", "mybatis", "hibernate",
        # Go
        "go", "golang", "gin",
        # 数据库
        "mysql", "mongodb", "redis", "postgresql", "neo4j", "milvus", "pinecone",
        "elasticsearch", "kafka", "rabbitmq",
        # AI/Agent
        "langchain", "langgraph", "rag", "agent", "mcp", "llm", "embedding", "reranker",
        "deepseek", "openai", "crewai", "autogen", "pytorch", "tensorflow",
        "coze", "dify", "openclaw", "harness", "ai coding", "aicoding",
        "workflow", "自动化", "数字员工", "prompt engineering",
        # 大数据
        "spark", "hadoop", "flink", "pandas", "tableau",
        # 工程/DevOps
        "docker", "kubernetes", "k8s", "git", "ci/cd", "github actions", "linux",
        "websocket", "sse", "uvicorn", "nginx", "jenkins", "terraform",
        # 前端
        "react", "vue", "javascript", "typescript", "html", "css", "webpack", "vite",
        "node.js", "nodejs", "express", "next.js", "angular",
        # 微服务/分布式
        "微服务", "分布式", "高并发", "rpc", "grpc",
    ]

    def match(self, jd_text: str, resume_text: str) -> dict:
        jd_lower = jd_text.lower()
        resume_lower = resume_text.lower()

        matched = []
        missing = []
        for kw in self.TECH_KEYWORDS:
            if kw in jd_lower:
                if kw in resume_lower:
                    matched.append(kw)
                else:
                    missing.append(kw)

        score = round(len(matched) / max(len(matched) + len(missing), 1), 2)
        logger.debug(f"技能匹配: matched={len(matched)}, missing={len(missing)}, score={score}")

        return {
            "score": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "match_rate": f"{len(matched)}/{len(matched) + len(missing)}",
        }


matcher = SkillMatcher()

from langchain_core.tools import tool


@tool
def match_skills(jd_text: str, resume_text: str) -> str:
    """对比 JD 和简历的技能匹配度。
    传入 JD 文本和简历文本，返回匹配的技能列表、缺失的技能列表和匹配率。
    """
    result = matcher.match(jd_text, resume_text)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    jd = "熟悉 Python FastAPI MySQL Docker LangGraph"
    resume = "Python FastAPI Redis Git Linux"
    print(match_skills.invoke({"jd_text": jd, "resume_text": resume}))
