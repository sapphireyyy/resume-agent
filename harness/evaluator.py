"""
Harness 评测引擎 — 4 维自动化评分
"""
import json
import time
from harness.adapter import adapter
from harness.dataset import get_dataset
from logger_config import setup_logger

logger = setup_logger("harness.evaluator")


# 中英文标签映射
LABEL_MAP = {
    "pass": "面试", "pending": "待定", "reject": "不匹配",
    "面试": "面试", "待定": "待定", "不匹配": "不匹配",
    "建议面试": "面试",
}


LABEL_MAP = {
    "pass": "建议面试", "pending": "待定", "reject": "不匹配",
    "建议面试": "建议面试", "面试": "建议面试",
    "待定": "待定", "不匹配": "不匹配",
}


def evaluate_conclusion(expected: str, result: dict) -> float:
    """维度1：结论正确性 (0-0.30)"""
    expected_cn = LABEL_MAP.get(str(expected).strip().lower(), str(expected).strip())
    conclusion = str(result.get("conclusion", "")).strip()
    actual_cn = LABEL_MAP.get(conclusion.lower(), conclusion)
    if actual_cn == expected_cn:
        return 0.30
    return 0.0


def evaluate_worker_count(result: dict) -> float:
    """维度2：Agent 覆盖度 (0-0.25)"""
    workers = result.get("activated_workers", [])
    return min(len(workers) * 0.08, 0.25)


def evaluate_report_structure(result: dict) -> float:
    """维度3：报告完整性 (0-0.25)"""
    score = 0.0
    if "conclusion" in result:
        score += 0.10
    if "details" in result:
        score += 0.15
    return min(score, 0.25)


def evaluate_speed(result: dict) -> float:
    """维度4：风险感知 (0-0.20)"""
    details = result.get("details", {})
    if isinstance(details, dict):
        risk_result = details.get("risk", "")
    else:
        risk_result = str(details)
    if any(w in str(risk_result).lower() for w in ["high", "medium", "flag", "risk"]):
        return 0.20
    return 0.10


def evaluate_case(case: dict) -> dict:
    t0 = time.time()
    logger.info(f"[{case['id']}] 开始评测, expected={case['expected']}")
    try:
        result = adapter.run(case["jd"], case["resume"])
    except Exception as e:
        logger.error(f"[{case['id']}] 执行失败: {e}", exc_info=True)
        result = {"conclusion": "error", "error": str(e)}

    scores = {
        "conclusion": evaluate_conclusion(case["expected"], result),
        "worker_coverage": evaluate_worker_count(result),
        "report_structure": evaluate_report_structure(result),
        "risk_awareness": evaluate_speed(result),
    }
    total = round(sum(scores.values()), 2)
    passed = total >= 0.70
    elapsed = round(time.time() - t0, 2)
    logger.info(
        f"[{case['id']}] 完成: total={total} passed={passed} "
        f"conclusion={scores['conclusion']:.2f} coverage={scores['worker_coverage']:.2f} "
        f"structure={scores['report_structure']:.2f} risk={scores['risk_awareness']:.2f} "
        f"actual={result.get('conclusion','?')} 耗时={elapsed}s"
    )
    return {
        "case_id": case["id"],
        "expected": case["expected"],
        "actual": result.get("conclusion", "?"),
        "passed": passed,
        "score": total,
        "scores_detail": scores,
        "workers": result.get("activated_workers", []),
    }


def run_harness() -> dict:
    t0 = time.time()
    logger.info("========== Harness 评测开始 ==========")
    dataset = get_dataset()
    logger.info(f"数据集加载: {len(dataset)} 个用例")
    results = []
    for i, c in enumerate(dataset):
        results.append(evaluate_case(c))
        # API 限流：每份简历间隔 3 秒
        if i < len(dataset) - 1:
            time.sleep(3)
    avg = round(sum(r["score"] for r in results) / len(results), 2)
    passed = sum(1 for r in results if r["passed"])
    elapsed = round(time.time() - t0, 2)
    summary = {"total": len(dataset), "passed": passed, "failed": len(dataset) - passed, "avg_score": avg, "details": results}
    with open("screen_harness_result.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary}, f, ensure_ascii=False, indent=2)
    logger.info(f"========== Harness 评测完成: passed={passed}/{len(dataset)}, avg={avg}, 耗时={elapsed}s ==========")
    return summary


if __name__ == "__main__":
    s = run_harness()
    print(f"总: {s['total']} | 通过: {s['passed']} | 均分: {s['avg_score']}")
