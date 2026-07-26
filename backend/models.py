"""数据库模型 — SQLite 默认，MySQL 可选"""
import os
import datetime
from dotenv import load_dotenv

# 确保加载 .env（项目根目录）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from logger_config import setup_logger

logger = setup_logger("backend.models")

# 优先 MYSQL_URL，否则用 SQLite（零配置）
DATABASE_URL = os.getenv("MYSQL_URL", "sqlite:///screener.db")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False)
Base = declarative_base()


class JobDescription(Base):
    """岗位表"""
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False, comment="岗位名称")
    content = Column(Text, nullable=False, comment="JD 全文")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 一对多：一个岗位有多个候选人
    candidates = relationship("Candidate", back_populates="job")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Candidate(Base):
    """候选人表"""
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="姓名")
    email = Column(String(100), nullable=True, comment="邮箱")
    phone = Column(String(20), nullable=True, comment="电话号码")
    gender = Column(String(10), nullable=True, comment="性别")
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True, comment="应聘岗位ID")
    resume_text = Column(Text, nullable=True, comment="简历原文")
    status = Column(String(20), default="待定", comment="筛选状态: 通过/待定/不匹配")
    score = Column(Float, nullable=True, comment="综合评分 0-1")
    reasoning = Column(Text, nullable=True, comment="评估理由")
    details = Column(JSON, nullable=True, comment="Agent 详细结果")
    workers = Column(JSON, nullable=True, comment="激活的 Worker")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("JobDescription", back_populates="candidates")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "gender": self.gender,
            "job_title": self.job.title if self.job else None,
            "job_id": self.job_id,
            "resume_preview": (self.resume_text or "")[:200],
            "status": self.status,
            "score": self.score,
            "reasoning": self.reasoning,
            "workers": self.workers,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info(f"数据库初始化完成: {DATABASE_URL}")


init_db()
