# -*- coding: utf-8 -*-
"""FastAPI backend - resume screening platform"""
import json, uuid, os, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from logger_config import setup_logger
logger = setup_logger("backend.main")

from backend.models import SessionLocal, JobDescription, Candidate, engine

app = FastAPI(title="resume-agent", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    logger.info("frontend mounted: %s", frontend_dir)

_task_status: dict[str, dict] = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Pydantic Models ====================

class JDCreate(BaseModel):
    title: str
    content: str


class ScreenTextRequest(BaseModel):
    jd_text: str
    resume_text: str


class ScreenResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None


class StatusUpdate(BaseModel):
    status: str


# ==================== JD API ====================

@app.post("/api/jd")
def create_jd(req: JDCreate, db: Session = Depends(get_db)):
    jd = JobDescription(title=req.title, content=req.content)
    db.add(jd)
    db.commit()
    db.refresh(jd)
    logger.info("created JD: %s", req.title)
    return jd.to_dict()


@app.get("/api/jd")
def list_jds(db: Session = Depends(get_db)):
    jds = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
    return [j.to_dict() for j in jds]


# ==================== Screening API ====================

@app.post("/api/screen/text", response_model=ScreenResponse)
def screen_text(req: ScreenTextRequest, bg: BackgroundTasks):
    task_id = str(uuid.uuid4())
    _task_status[task_id] = {"status": "pending"}
    logger.info("text screening request task_id=%s", task_id[:8])
    bg.add_task(_run_screening, task_id, req.jd_text, req.resume_text)
    return ScreenResponse(task_id=task_id, status="pending")


@app.post("/api/screen/pdf")
async def screen_pdf(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    gender: str = Form(""),
    job_id: Optional[int] = Form(None),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "PDF only")
    pdf_bytes = await file.read()
    task_id = str(uuid.uuid4())
    _task_status[task_id] = {"status": "pending", "filename": file.filename}
    logger.info("PDF screening request task_id=%s file=%s", task_id[:8], file.filename)

    meta = {"name": name, "email": email, "phone": phone, "gender": gender, "job_id": job_id}
    bg.add_task(_run_pdf_screening, task_id, jd_text, pdf_bytes, file.filename, meta)
    return ScreenResponse(task_id=task_id, status="pending")


@app.get("/api/screen/{task_id}")
def get_result(task_id: str, db: Session = Depends(get_db)):
    t = _task_status.get(task_id)
    if t:
        return ScreenResponse(task_id=task_id, status=t["status"],
                              result=t.get("result"), resume_text=t.get("resume_text"))

    c = db.query(Candidate).filter(Candidate.id == int(task_id) if task_id.isdigit() else None).first()
    if not c:
        raise HTTPException(404, "task not found")
    result = {
        "conclusion": c.status, "reasoning": c.reasoning,
        "score": c.score, "details": c.details,
        "activated_workers": c.workers or [],
    }
    return ScreenResponse(task_id=str(c.id), status="done", result=result)


# ==================== Candidate API ====================

@app.get("/api/candidates")
def list_candidates(
    job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1), limit: int = Query(20),
    db: Session = Depends(get_db),
):
    q = db.query(Candidate)
    if job_id is not None:
        q = q.filter(Candidate.job_id == job_id)
    if status:
        q = q.filter(Candidate.status == status)
    total = q.count()
    items = q.order_by(Candidate.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"page": page, "limit": limit, "total": total, "items": [c.to_dict() for c in items]}


@app.put("/api/candidates/{candidate_id}/status")
def update_status(candidate_id: int, req: StatusUpdate, db: Session = Depends(get_db)):
    c = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(404, "candidate not found")
    old = c.status
    c.status = req.status
    db.commit()
    logger.info("candidate %s: %s -> %s", c.name, old, req.status)
    return c.to_dict()


# ==================== Stats ====================

@app.get("/api/stats")
def stats(job_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Candidate)
    if job_id is not None:
        q = q.filter(Candidate.job_id == job_id)
    total = q.count()
    return {
        "total": total,
        "pass": q.filter(Candidate.status == "通过").count(),
        "pending": q.filter(Candidate.status == "待定").count(),
        "reject": q.filter(Candidate.status == "不匹配").count(),
    }


# ==================== Harness ====================

@app.post("/api/harness/run")
def run_harness():
    from harness.evaluator import run_harness
    return run_harness()


# ==================== Pages ====================

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>frontend not found</h1>"


@app.get("/health")
def health():
    checks = {}

    if os.getenv("DEEPSEEK_API_KEY"):
        checks["model"] = {"status": "ok"}
    else:
        checks["model"] = {"status": "error", "error": "DEEPSEEK_API_KEY 未设置"}

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        logger.error("数据库启动检查失败: %s", exc)
        checks["database"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    pdf_providers = []
    try:
        import pypdf  # noqa: F401
        pdf_providers.append("pypdf")
    except ImportError:
        pass
    if os.getenv("MINERU_API_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}:
        pdf_providers.append("mineru-precision-api")
    if pdf_providers:
        checks["pdf"] = {"status": "ok", "providers": pdf_providers}
    else:
        checks["pdf"] = {"status": "error", "error": "未启用 MinerU API 且未找到 pypdf"}

    ready = all(check["status"] == "ok" for check in checks.values())
    return {"status": "ok" if ready else "degraded", "ready": ready, "checks": checks}


# ==================== Background Tasks ====================

def _run_screening(task_id: str, jd: str, resume: str):
    from screening_engine.supervisor_graph import screen_resume
    try:
        _task_status[task_id]["status"] = "running"
        t0 = time.time()
        result = screen_resume(jd, resume)
        elapsed = round(time.time() - t0, 1)
        result_status = result.get("details", {}).get("reliability", {}).get("status")
        task_status = "degraded" if result_status == "degraded" else "done"
        logger.info("screening done task_id=%s conclusion=%s time=%ss", task_id[:8], result.get("conclusion"), elapsed)
        _task_status[task_id] = {"status": task_status, "result": result, "resume_text": resume}
    except Exception as e:
        logger.error("screening failed task_id=%s: %s", task_id[:8], e, exc_info=True)
        _task_status[task_id] = {"status": "failed", "error": str(e)}


def _run_pdf_screening(task_id: str, jd: str, pdf_bytes: bytes, filename: str, meta: dict):
    from skills.parse_resume.parser import parser as pdf_parser
    try:
        _task_status[task_id]["status"] = "parsing"
        parse_result = pdf_parser.parse(pdf_bytes, filename)
        if parse_result["status"] != "ok":
            _task_status[task_id] = {"status": "failed", "error": parse_result.get("error", "PDF parse failed")}
            return
        resume_text = parse_result["text"]
        _task_status[task_id]["resume_text"] = resume_text

        _task_status[task_id]["status"] = "running"
        from screening_engine.supervisor_graph import screen_resume
        t0 = time.time()
        result = screen_resume(jd, resume_text, parse_result.get("sections"))
        elapsed = round(time.time() - t0, 1)
        result_status = result.get("details", {}).get("reliability", {}).get("status")
        task_status = "degraded" if result_status == "degraded" else "done"

        _task_status[task_id] = {"status": task_status, "result": result, "resume_text": resume_text}
        _save_candidate(meta, resume_text, result, elapsed, jd)
    except Exception as e:
        logger.error("PDF screening failed task_id=%s: %s", task_id[:8], e, exc_info=True)
        _task_status[task_id] = {"status": "failed", "error": str(e)}


def _save_candidate(meta: dict, resume_text: str, result: dict, elapsed: float, jd_text: str):
    db = SessionLocal()
    try:
        job_id = meta.get("job_id")
        if job_id:
            job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
        else:
            jd_preview = jd_text[:100]
            job = db.query(JobDescription).filter(JobDescription.content.like(f"{jd_preview}%")).first()
            if not job:
                job = JobDescription(title=f"temp_{meta.get('name','unknown')}", content=jd_text)
                db.add(job)
                db.flush()

        c = Candidate(
            name=meta.get("name") or f"anon_{uuid.uuid4().hex[:6]}",
            email=meta.get("email") or None,
            phone=meta.get("phone") or None,
            gender=meta.get("gender") or None,
            job_id=job.id,
            resume_text=resume_text,
            status=result.get("conclusion", "待定"),
            score=result.get("score"),
            reasoning=result.get("reasoning"),
            details=result.get("details"),
            workers=result.get("activated_workers"),
        )
        db.add(c)
        db.commit()
        logger.info("candidate saved: %s -> %s (job: %s)", c.name, c.status, job.title)
    except Exception as e:
        db.rollback()
        logger.error("failed to save candidate: %s", e)
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    logger.info("========== resume-agent starting ==========")
    uvicorn.run(app, host="0.0.0.0", port=8000)
