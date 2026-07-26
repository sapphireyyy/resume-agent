"""
经历评分 Skill — 评估项目深度、实习质量、技术栈匹配度
走 LLM，因为项目描述的语义判断硬规则做不了
"""
import json
from typing import Callable
from logger_config import setup_logger
from prompts.experience_scorer import EXPERIENCE_SCORER_PROMPT

logger = setup_logger("skills.experience_score")


class ExperienceScorer:
    def __init__(self, llm_fn: Callable):
        self._llm = llm_fn

    def score(self, resume_text: str) -> dict:
        try:
            logger.debug("调用 LLM 评估经历...")
            response = self._llm.invoke([
                {"role": "system", "content": EXPERIENCE_SCORER_PROMPT},
                {"role": "user", "content": resume_text},
            ])
            result = json.loads(response.content)
            logger.debug(f"经历评分: project={result.get('project_score')}, internship={result.get('internship_score')}")
            return result
        except Exception as e:
            logger.error(f"经历评分失败: {e}")
            return {"project_score": 0.5, "internship_score": 0.5, "strengths": [], "weaknesses": ["分析失败"]}


_scorer: ExperienceScorer | None = None


def get_scorer() -> ExperienceScorer:
    global _scorer
    if _scorer is None:
        from langchain.chat_models import init_chat_model
        _scorer = ExperienceScorer(init_chat_model("deepseek-chat"))
    return _scorer


from langchain_core.tools import tool


@tool
def score_experience(resume_text: str) -> str:
    """评估简历中项目经历和实习经历的质量。
    传入简历文本，返回项目评分、实习评分、亮点和不足。
    """
    result = get_scorer().score(resume_text)
    return json.dumps(result, ensure_ascii=False)
