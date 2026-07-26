"""
风险检测 Skill — 识别简历中的红旗信号（硬规则）
"""
import json
import re
from logger_config import setup_logger

logger = setup_logger("skills.risk_check")

RISK_RULES = [
    {
        "id": "R01",
        "name": "频繁跳槽",
        "check": lambda text: len(re.findall(r'\d{4}-\d{2}\s*[~～至到]\s*\d{4}-\d{2}', text)) >= 4,
        "detail": "近 2 年超过 3 段工作经历"
    },
    {
        "id": "R02",
        "name": "空窗期标记",
        "check": lambda text: bool(re.search(r'(?:空窗|gap|待业).*?(?:年|月)', text)),
        "detail": "简历中出现空窗期描述，需结合上下文判断（创业/进修/家庭原因等）"
    },
    {
        "id": "R03",
        "name": "技能堆砌",
        "check": lambda text: len(re.findall(r'(?:熟悉|掌握|精通|了解)', text)) > 10,
        "detail": "技能关键词过多（>10个），可能注水"
    },
    {
        "id": "R04",
        "name": "缺少量化结果",
        "check": lambda text: not re.search(r'(?:提升|降低|减少|增长)\s*\d+%?', text) and len(text) > 200,
        "detail": "项目描述缺少量化成果"
    },
    {
        "id": "R05",
        "name": "学历信息标记",
        "check": lambda text: bool(re.search(r'(?:专科|大专|高中|中专)', text)),
        "detail": "学历信息与岗位常见要求存在差异，需结合经历综合评估，不做自动扣分"
    },
]


class RiskChecker:
    def check(self, resume_text: str) -> dict:
        flags = []
        for rule in RISK_RULES:
            if rule["check"](resume_text):
                flags.append({"rule_id": rule["id"], "name": rule["name"], "detail": rule["detail"]})

        severity = "low"
        if len(flags) >= 3:
            severity = "high"
        elif len(flags) >= 1:
            severity = "medium"

        logger.debug(f"风险检测: flags={len(flags)}, severity={severity}, rules={[f['rule_id'] for f in flags]}")
        return {"flags": flags, "count": len(flags), "severity": severity}


checker = RiskChecker()

from langchain_core.tools import tool


@tool
def check_risks(resume_text: str) -> str:
    """检测简历中的风险信号：频繁跳槽、空窗期、技能注水、缺少量化。
    传入简历文本，返回红旗列表和风险等级。
    """
    result = checker.check(resume_text)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    test = "2023-01~2023-06 A公司\n2023-07~2024-01 B公司\n2024-02~2024-08 C公司\n2024-09~2025-03 D公司"
    print(check_risks.invoke(test))
