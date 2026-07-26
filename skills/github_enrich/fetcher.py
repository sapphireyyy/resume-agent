"""
GitHub 数据增强 Skill — 提取简历中的 GitHub 用户名，调 API 获取仓库信息
"""
import json
import re
import os
from typing import Optional
from langchain_core.tools import tool
from logger_config import setup_logger

logger = setup_logger("skills.github_enrich")


class GitHubEnricher:
    """从简历文本提取 GitHub 用户名，获取仓库信息作为评估增强数据"""

    def extract_username(self, text: str) -> Optional[str]:
        """从文本中提取 GitHub 用户名"""
        patterns = [
            r'github\.com/([a-zA-Z0-9\-_]+)',          # github.com/username
            r'GitHub[\s:：]*@?([a-zA-Z0-9\-_]+)',      # GitHub @username 或 GitHub: username
            r'github[\s:：]*@?([a-zA-Z0-9\-_]+)',      # github @username
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                username = m.group(1).strip()
                # 过滤掉非用户名的路径
                if username not in ("issues", "pull", "pulls", "settings", "notifications", "explore"):
                    return username
        return None

    def fetch_repos(self, username: str) -> dict:
        """调用 GitHub API 获取用户仓库"""
        try:
            import urllib.request
            token = os.getenv("GITHUB_TOKEN", "")
            url = f"https://api.github.com/users/{username}/repos?sort=stars&per_page=10"
            req = urllib.request.Request(url, headers={"User-Agent": "resume-agent"})
            if token:
                req.add_header("Authorization", f"Bearer {token}")

            with urllib.request.urlopen(req, timeout=10) as resp:
                repos = json.loads(resp.read().decode())

            result = []
            for r in repos:
                result.append({
                    "name": r.get("name", ""),
                    "stars": r.get("stargazers_count", 0),
                    "forks": r.get("forks_count", 0),
                    "language": r.get("language", ""),
                    "description": r.get("description", "") or "",
                    "topics": r.get("topics", []),
                    "pushed_at": r.get("pushed_at", ""),
                })

            logger.info(f"GitHub API 返回 {len(result)} 个仓库 (用户: {username})")
            return {"status": "ok", "username": username, "repo_count": len(result), "repos": result}
        except Exception as e:
            logger.warning(f"GitHub API 调用失败 (用户: {username}): {e}")
            return {"status": "error", "username": username, "error": str(e)}

    def enrich(self, resume_text: str) -> dict:
        username = self.extract_username(resume_text)
        if not username:
            logger.debug("未在简历中找到 GitHub 用户名")
            return {"status": "no_github", "message": "未在简历中找到 GitHub 用户名"}
        logger.info(f"提取到 GitHub 用户名: {username}")
        return self.fetch_repos(username)


enricher = GitHubEnricher()


@tool
def enrich_github(resume_text: str) -> str:
    """从简历文本中提取 GitHub 用户名，获取用户仓库信息（stars/forks/语言/描述）。
    返回仓库列表，用于评估候选人的开源贡献和技术活跃度。
    """
    result = enricher.enrich(resume_text)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    test = "GitHub: https://github.com/eyb123456 熟悉 Python"
    print(enrich_github.invoke(test))
