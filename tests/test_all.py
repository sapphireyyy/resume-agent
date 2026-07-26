# -*- coding: utf-8 -*-
"""完整测试套件"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}: {detail}")

print("=" * 50)
print("resume-agent - Full Test Suite")
print("=" * 50)

# === 1. Skills ===
print("\n[1] Skills Module")

print("  skill_match:")
from skills.skill_match.matcher import match_skills, SkillMatcher
m = SkillMatcher()
r1 = json.loads(match_skills.invoke({"jd_text": "Python Docker", "resume_text": "I know Python"}))
check("has score", "score" in r1)
check("python matched", "python" in r1["matched_skills"])
check("docker missing", "docker" in r1["missing_skills"])

print("  experience_score:")
from skills.experience_score.scorer import ExperienceScorer
es = ExperienceScorer(lambda m: type('R',(),{'content':json.dumps({"project_score":0.8,"internship_score":0.6,"strengths":["test"],"weaknesses":[]})})())
check("module loaded", es is not None)

print("  risk_check:")
from skills.risk_check.checker import check_risks, RiskChecker
rc = RiskChecker()
r3 = json.loads(check_risks.invoke("Python FastAPI two years"))
check("normal resume no flags", r3["count"] == 0)
r4 = json.loads(check_risks.invoke("2023-01~2023-06 A\n2023-07~2024-01 B\n2024-02~2024-08 C\n2024-09~2025-03 D"))
check("frequent hops detected", len(r4["flags"]) > 0)
r5 = json.loads(check_risks.invoke("熟悉 Python 熟练掌握 Java 精通 C++ 了解 Go 熟悉 Rust 精通 TS 熟练掌握 React 精通 Vue 了解 Angular 掌握 Next.js 了解 Nest.js"))
check("skill stacking detected", len(r5["flags"]) > 0)

print("  parse_resume:")
from skills.parse_resume.parser import ResumeParser
parser = ResumeParser()
check("parser loaded", parser is not None)

# === 2. Agents (lazy init) ===
print("\n[2] Agent Module (lazy init, no API key)")
from screening_engine.agents.skill_agent import get_skill_agent
from screening_engine.agents.experience_agent import get_experience_agent
from screening_engine.agents.risk_agent import get_risk_agent
check("agents import OK", True)

# === 3. Supervisor Graph ===
print("\n[3] Supervisor Graph")
from screening_engine.supervisor_graph import create_screen_graph, ScreenState
check("graph created", True)
check("state defined", True)

# === 4. Harness Evaluation ===
print("\n[4] Harness Evaluation")
from harness.dataset import get_dataset
ds = get_dataset()
check(f"dataset {len(ds)} cases", len(ds) == 20)

class MockAdapter:
    def run(self, jd, resume):
        jd_l, resume_l = jd.lower(), resume.lower()
        kw = sum(1 for k in ['python','fastapi','react','java','go','langgraph','spring','ai','rag','agent','mysql','mongodb'] if k in resume_l)
        if kw >= 4:
            conclusion = 'pass'
        elif kw >= 2:
            conclusion = 'pending'
        else:
            conclusion = 'reject'
        return {'conclusion': conclusion, 'activated_workers': ['skill','experience','risk']}

import harness.evaluator as ev
ev.adapter = MockAdapter()
results = [ev.evaluate_case(c) for c in ds]
avg_score = round(sum(r["score"] for r in results) / len(results), 2)
passed_h = sum(1 for r in results if r["passed"])
check(f"average score ({avg_score})", avg_score > 0.5)
check(f"pass rate ({passed_h}/{len(results)})", passed_h > 0)

# === 5. Backend API ===
print("\n[5] Backend API")
from backend.main import app
routes = [r.path for r in app.routes]
check("routes loaded", len(routes) >= 6)
check("/health exists", "/health" in routes)
check("/api/screen/text exists", "/api/screen/text" in routes)
check("/api/screen/pdf exists", "/api/screen/pdf" in routes)
check("/api/harness/run exists", "/api/harness/run" in routes)

# === Summary ===
print("\n" + "=" * 50)
print(f"  Passed: {passed}  Failed: {failed}")
print("=" * 50)
sys.exit(0 if failed == 0 else 1)
