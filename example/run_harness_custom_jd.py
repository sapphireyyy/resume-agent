"""Harness 一键运行 — 使用自定义 JD"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger_config import setup_logger
logger = setup_logger("example.run_harness_custom_jd")

from harness.adapter import adapter
from harness.dataset import get_dataset

# ==================== 自定义 AI 工程岗 JD ====================
AI_APP_JD = """职位详情
1、负责AI提效相关工作的设计、开发和落地，围绕组织效率提升、研发方式升级和AI-Native工作模式建设，推动关键项目形成可复用、可推广的实践;
2、负责AICoding方向的工程化落地，推进代码生成、测试辅助、代码评审、研发协同等能力进入真实研发流程，推动Harness Engineering等前沿实践沉淀为团队级方法论和工程标准;
3、负责AIAgent方向的探索与落地，推动OpenClaw等Agent框架在办公、研发、协同等场景中的实际应用，推进数字员工方案从Demo走向稳定运行;
4、负责相关能力的平台化与治理建设，明确协作机制、权限控制、风险治理、效果评估与可观测性要求，保障能力可用、可信、可规模化推广;
5、结合实际业务场景，持续优化AI能力接入方式、Workflow设计和系统稳定性，推动AI能力在真实环境中长期发挥价值。

职位要求
1、有AIEngineering、研发效能、工程平台、自动化工作流或相关方向的实践经验，能够独立推进功能落地与方案实现;
2、具备扎实的工程能力，有AICoding工程化实践经验优先;有AIAgent、自动化工作流、数字员工或企业级协同系统相关实践经验优先;
3、对AI前沿方向有深刻理解，尤其对AICoding、Agent、模型能力演进等方向保持持续关注，能够结合业务场景完成技术选型与落地实现;
4、具备良好的工程化思维，能够将快速变化的AI能力转化为稳定、可维护、可扩展的工程方案;
5、有较强的问题拆解与协同推进能力，能够在复杂场景下与产品、业务、平台、研发等角色高效协作;
6、对新技术保持好奇心和执行力，愿意持续学习并推动AI能力在组织中的真实落地。

加分项:
1、有Harness Engineering、Agent平台、企业级AI工作流、数字员工体系等相关实践经验;
2、有OpenClaw、Copilot类产品、Code Agent、自动化协同系统等实际落地经验;
3、持续关注并输出AI前沿趋势判断、实践总结或方法论沉淀。"""


def run_with_custom_jd(jd_text: str, jd_label: str = "AI应用岗"):
    dataset = get_dataset()
    results = []

    print("=" * 60)
    print(f"  Harness 评测 — 统一 JD: {jd_label}")
    print("=" * 60)
    print()

    for i, case in enumerate(dataset):
        case_id = case["id"]
        resume = case["resume"]
        print(f"[{i+1}/{len(dataset)}] {case_id} 评估中...", end=" ", flush=True)

        try:
            result = adapter.run(jd_text, resume)
            conclusion = result.get("conclusion", "?")
            workers = result.get("activated_workers", [])
            print(f"→ {conclusion} (Workers: {workers})")
        except Exception as e:
            conclusion = "error"
            workers = []
            result = {"conclusion": "error", "error": str(e)}
            print(f"→ ERROR: {str(e)[:80]}")

        results.append({
            "case_id": case_id,
            "resume_preview": resume[:80] + "...",
            "conclusion": conclusion,
            "workers": workers,
            "result": result,
        })

        # API 限流：每份简历间隔 3 秒
        if i < len(dataset) - 1:
            time.sleep(3)

    # 统计
    interview = sum(1 for r in results if "面试" in r["conclusion"])
    pending = sum(1 for r in results if "待定" in r["conclusion"])
    reject = sum(1 for r in results if "不匹配" in r["conclusion"])
    error = sum(1 for r in results if r["conclusion"] == "error")

    print()
    print("=" * 60)
    print(f"  评测结果 — JD: {jd_label}")
    print("=" * 60)
    print(f"  总用例: {len(results)}")
    print(f"  ✅ 建议面试: {interview}")
    print(f"  ⚡ 待定:     {pending}")
    print(f"  ❌ 不匹配:   {reject}")
    print(f"  💥 错误:     {error}")
    print("-" * 60)
    for r in results:
        icon = {"面试":"✅","待定":"⚡","不匹配":"❌","error":"💥"}.get(
            next((k for k in ["面试","待定","不匹配","error"] if k in r["conclusion"]), "?"
        , "?"))
        print(f"  {icon} {r['case_id']:15s} → {r['conclusion']:6s}  |  {r['resume_preview']}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    run_with_custom_jd(AI_APP_JD, "大模型AI应用开发")
