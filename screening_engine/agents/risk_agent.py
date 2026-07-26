"""Worker 3: 风险检测 Agent"""
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from skills.risk_check.checker import check_risks
from logger_config import setup_logger
from prompts.risk_agent import RISK_AGENT_PROMPT

logger = setup_logger("screening.risk_agent")

_risk_agent = None

def get_risk_agent():
    global _risk_agent
    if _risk_agent is None:
        logger.info("初始化 Risk Agent (deepseek-chat + check_risks)")
        llm = init_chat_model("deepseek-chat")
        _risk_agent = create_react_agent(model=llm, tools=[check_risks], prompt=RISK_AGENT_PROMPT, name="risk_agent")
    return _risk_agent
