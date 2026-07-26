"""Worker 0: 简历解析 Agent — 将原始文本分段提取为结构化 JSON"""
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from logger_config import setup_logger
from prompts.parser_agent import PARSER_AGENT_PROMPT

logger = setup_logger("screening.parser_agent")

_parser_agent = None

def get_parser_agent():
    global _parser_agent
    if _parser_agent is None:
        logger.info("初始化 Parser Agent (deepseek-chat)")
        llm = init_chat_model("deepseek-chat")
        _parser_agent = create_react_agent(
            model=llm,
            tools=[],
            prompt=PARSER_AGENT_PROMPT,
            name="parser_agent",
        )
    return _parser_agent
