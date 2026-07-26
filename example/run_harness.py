"""Harness 一键运行"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger_config import setup_logger
logger = setup_logger("example.run_harness")

from harness.evaluator import run_harness

if __name__ == "__main__":
    logger.info("启动 Harness 一键评测")
    s = run_harness()
    print("=" * 50)
    print("简历筛选 Harness 评测")
    print("=" * 50)
    print(f"总用例: {s['total']} | 通过: {s['passed']} | 均分: {s['avg_score']}")
    for d in s["details"]:
        icon = "✅" if d["passed"] else "❌"
        print(f"  {icon} {d['case_id']}: {d['score']} (expected={d['expected']}, actual={d['actual']})")
    logger.info("Harness 一键评测结束")
