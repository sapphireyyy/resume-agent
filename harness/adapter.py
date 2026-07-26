"""Harness Agent 适配器"""
from screening_engine.supervisor_graph import screen_resume


class ScreenAdapter:
    def run(self, jd: str, resume: str) -> dict:
        return screen_resume(jd, resume)


adapter = ScreenAdapter()
