"""Worker 1: 技能匹配 Agent"""
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from skills.skill_match.matcher import match_skills
from logger_config import setup_logger
from prompts.skill_agent import SKILL_AGENT_PROMPT

logger = setup_logger("screening.skill_agent")

_skill_agent = None

def get_skill_agent():
    global _skill_agent
    if _skill_agent is None:
        logger.info("初始化 Skill Agent (deepseek-chat + match_skills)")
        llm = init_chat_model("deepseek-chat")
        _skill_agent = create_react_agent(model=llm, tools=[match_skills], prompt=SKILL_AGENT_PROMPT, name="skill_agent")
    return _skill_agent
