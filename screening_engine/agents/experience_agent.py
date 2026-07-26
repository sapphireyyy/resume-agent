"""Worker 2: 经历评分 Agent"""
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from skills.experience_score.scorer import score_experience
from logger_config import setup_logger
from prompts.experience_agent import EXPERIENCE_AGENT_PROMPT

logger = setup_logger("screening.experience_agent")

_experience_agent = None

def get_experience_agent():
    global _experience_agent
    if _experience_agent is None:
        logger.info("初始化 Experience Agent (deepseek-chat + score_experience)")
        llm = init_chat_model("deepseek-chat")
        _experience_agent = create_react_agent(model=llm, tools=[score_experience], prompt=EXPERIENCE_AGENT_PROMPT, name="experience_agent")
    return _experience_agent
