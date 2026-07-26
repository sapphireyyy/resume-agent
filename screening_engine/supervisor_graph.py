"""
Supervisor 图 — ReAct 风格多 Agent 简历筛选
Supervisor 是 ReAct Agent，3 个 Worker 作为它的 Tool；
每次 Worker 返回后，Supervisor 观察结果再决定下一步。
"""
import json
import time
from typing import TypedDict, Annotated

from dotenv import load_dotenv
load_dotenv()

from logger_config import setup_logger
logger = setup_logger("screening.supervisor")

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import AIMessage

# ==================== State ====================

class ScreenState(TypedDict):
    messages: Annotated[list, add_messages]
    jd_text: str
    resume_text: str
    results: dict


# ==================== Worker Tools（给 Supervisor 调用） ====================

@tool
def call_parser_agent(context_hint: str = "") -> str:
    """简历结构化解析：将原始简历文本分段提取为 basics/work/education/skills/projects 结构化 JSON。
    调用时机：Supervisor 评估开始前，先把简历从一坨文本变成结构化字段
    
    Args:
        context_hint: Supervisor 的引导（如"注意区分项目经历和工作经历"）
    """
    from screening_engine.agents.parser_agent import get_parser_agent
    logger.info("    >>> [Parser Agent] 被 Supervisor 召唤")
    t0 = time.time()
    hint = f"{context_hint}\n\n简历原文:\n{_resume}"
    r = get_parser_agent().invoke({"messages": [("human", hint)]})
    logger.info(f"    <<< [Parser Agent] 回报 Supervisor (耗时 {round(time.time()-t0,1)}s)")
    return r["messages"][-1].content


@tool
def call_skill_agent(context_hint: str = "") -> str:
    """技能匹配检查：对比 JD 和简历的技术栈，返回匹配技能、缺失技能、匹配率。
    调用时机：Supervisor 想先看候选人的技能是否对得上 JD
    
    Args:
        context_hint: Supervisor 给 Agent 的额外提示（可选，如"重点查 Redis 和 K8s"）
    """
    from screening_engine.agents.skill_agent import get_skill_agent
    logger.info("    >>> [Skill Agent] 被 Supervisor 召唤")
    t0 = time.time()
    r = get_skill_agent().invoke({"messages": [("human", f"{context_hint}\n{_jd}\n\n{_resume}")]})
    logger.info(f"    <<< [Skill Agent] 回报 Supervisor (耗时 {round(time.time()-t0,1)}s)")
    return r["messages"][-1].content


@tool
def call_experience_agent(context_hint: str = "") -> str:
    """经历评估：分析项目深度、实习质量、技术栈匹配度，返回评分、亮点、不足。
    调用时机：Supervisor 看到技能匹配尚可，想深挖项目经历是否扎实
    
    Args:
        context_hint: Supervisor 的引导（如"技能匹配显示 Redis 缺失，看看他项目里有没有实际用过"）
    """
    from screening_engine.agents.experience_agent import get_experience_agent
    logger.info("    >>> [Experience Agent] 被 Supervisor 召唤")
    t0 = time.time()
    hint = f"{context_hint}\n\n简历内容:\n{_resume}"
    r = get_experience_agent().invoke({"messages": [("human", hint)]})
    logger.info(f"    <<< [Experience Agent] 回报 Supervisor (耗时 {round(time.time()-t0,1)}s)")
    return r["messages"][-1].content


@tool
def call_risk_agent(context_hint: str = "") -> str:
    """风险检测：查频繁跳槽、空窗期、技能注水、缺少量化、学历差距等红旗信号。
    调用时机：Supervisor 有其他 Agent 的回报后发现疑点，需要交叉验证
    
    Args:
        context_hint: Supervisor 的提示（如"技能 Agent 说 Redis 是简历写的但经历没体现，重点看技能注水"）
    """
    from screening_engine.agents.risk_agent import get_risk_agent
    logger.info("    >>> [Risk Agent] 被 Supervisor 召唤")
    t0 = time.time()
    hint = f"{context_hint}\n\n简历内容:\n{_resume}"
    r = get_risk_agent().invoke({"messages": [("human", hint)]})
    logger.info(f"    <<< [Risk Agent] 回报 Supervisor (耗时 {round(time.time()-t0,1)}s)")
    return r["messages"][-1].content


# ==================== Supervisor ReAct Agent ====================

from prompts.supervisor import SUPERVISOR_SYSTEM_PROMPT


def _make_supervisor_agent():
    """创建 ReAct Supervisor Agent"""
    llm = init_chat_model("deepseek-chat")
    return create_react_agent(
        model=llm,
        tools=[call_parser_agent, call_skill_agent, call_experience_agent, call_risk_agent],
        prompt=SUPERVISOR_SYSTEM_PROMPT,
        name="supervisor",
    )


# ==================== 图节点 ====================

# 全局变量，在 runtime 注入（因为 graph 编译时需要）
_jd = ""
_resume = ""


def supervisor_react_node(state: ScreenState) -> dict:
    """Supervisor ReAct 节点：运行 ReAct 循环，自行决定调用哪些 Worker"""
    global _jd, _resume
    _jd = state["jd_text"]
    # 截断过长简历，防止 API 超时（保留前 2000 字符足够判断技能/经历/风险）
    raw_resume = state["resume_text"]
    _resume = raw_resume[:2000] if len(raw_resume) > 2000 else raw_resume

    logger.info(f">>> [Supervisor] ReAct 循环启动, JD={len(_jd)}字符, 简历={len(_resume)}字符")
    t0 = time.time()

    supervisor = _make_supervisor_agent()
    result = supervisor.invoke({
        "messages": [("human", f"岗位要求:\n{_jd}\n\n候选人简历:\n{_resume}\n\n请开始评估。")]
    })

    last_msg = result["messages"][-1]
    reply = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # 尝试从最后一条消息提取 JSON 结论
    conclusion = "待定"
    reasoning = ""
    workers = []
    try:
        # 找最后一个 JSON 块
        if "{" in reply and "}" in reply:
            json_str = reply[reply.rindex("{"):reply.rindex("}")+1]
            parsed = json.loads(json_str)
            conclusion = parsed.get("conclusion", "待定")
            reasoning = parsed.get("reasoning", "")
            workers = parsed.get("activated_workers", [])
    except (json.JSONDecodeError, ValueError):
        pass

    elapsed = round(time.time() - t0, 1)
    logger.info(f"<<< [Supervisor] ReAct 循环结束, 结论={conclusion}, Workers={workers}, 耗时={elapsed}s")

    return {
        "messages": [AIMessage(content=reply)],
        "results": {"conclusion": conclusion, "reasoning": reasoning, "details": reply, "activated_workers": workers},
    }


# ==================== 图构建 ====================

def create_screen_graph():
    builder = StateGraph(ScreenState)
    builder.add_node("supervisor", supervisor_react_node)
    builder.add_edge(START, "supervisor")
    builder.add_edge("supervisor", END)
    return builder.compile()


screen_graph = create_screen_graph()


def screen_resume(jd_text: str, resume_text: str) -> dict:
    t0 = time.time()
    logger.info("=" * 60)
    logger.info(f"[Screen] 接收筛选请求 (JD={len(jd_text)}字符, 简历={len(resume_text)}字符)")
    result = screen_graph.invoke({
        "messages": [],
        "jd_text": jd_text,
        "resume_text": resume_text,
        "results": {},
    })
    elapsed = round(time.time() - t0, 1)
    logger.info(f"[Screen] 筛选完成 (总耗时={elapsed}s)")
    return result.get("results", {})


if __name__ == "__main__":
    jd = "Python FastAPI LangGraph MySQL Docker，三年经验"
    cv = "熟悉 Python FastAPI，做过 RAG 项目，掌握 Docker 部署，Git 版本管理"
    report = screen_resume(jd, cv)
    print(json.dumps(report, ensure_ascii=False, indent=2))
