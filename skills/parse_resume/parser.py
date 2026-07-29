"""Resume PDF parsing through MinerU's precision extraction API."""
import base64
import json
import os
import time
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from langchain_core.tools import tool
from dotenv import load_dotenv

from logger_config import setup_logger
from skills.parse_resume.sections import segment_resume

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

logger = setup_logger("skills.parse_resume")


class MinerUParseError(RuntimeError):
    """Raised when the MinerU precision API cannot parse a document."""


class ResumeParser:
    """Parse a PDF with MinerU precision API, optionally falling back to pypdf."""

    MAX_PRECISION_BYTES = 200 * 1024 * 1024

    def __init__(self):
        self.api_base_url = os.getenv(
            "MINERU_API_BASE_URL", "https://mineru.net/api/v4"
        ).rstrip("/")
        self.api_token = os.getenv("MINERU_API_TOKEN", "").strip()
        self.model_version = os.getenv("MINERU_MODEL_VERSION", "vlm")
        self.language = os.getenv("MINERU_LANGUAGE", "ch")
        self.request_timeout = float(os.getenv("MINERU_REQUEST_TIMEOUT_SECONDS", "30"))
        self.poll_interval = float(os.getenv("MINERU_POLL_INTERVAL_SECONDS", "3"))
        self.poll_timeout = float(os.getenv("MINERU_POLL_TIMEOUT_SECONDS", "600"))
        self.api_enabled = self._env_bool("MINERU_API_ENABLED", True)
        self.fallback_to_pypdf = self._env_bool("MINERU_FALLBACK_TO_PYPDF", True)

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def parse(self, pdf_bytes: bytes, filename: str = "resume.pdf") -> dict:
        safe_filename = Path(filename or "resume.pdf").name or "resume.pdf"
        api_error = None
        try:
            if not self.api_enabled:
                raise MinerUParseError("MinerU API 已通过 MINERU_API_ENABLED 禁用")
            text = self._parse_with_mineru_api(pdf_bytes, safe_filename)
            source = "mineru_api"
            logger.info("MinerU 精准 API 解析成功, 文本长度=%s", len(text))
        except Exception as exc:
            api_error = exc
            logger.warning("MinerU 精准 API 解析失败: %s", exc)
            if not self.fallback_to_pypdf:
                return self._error_result("mineru_api", exc)

            try:
                logger.info("尝试使用 pypdf 兜底解析...")
                text = self._parse_with_pypdf(pdf_bytes)
                source = "pypdf_fallback"
                logger.info("pypdf 兜底解析成功, 文本长度=%s", len(text))
            except Exception as fallback_exc:
                logger.error("MinerU 精准 API 和 pypdf 均解析失败", exc_info=True)
                return self._error_result(
                    "none", f"MinerU API: {api_error}; pypdf: {fallback_exc}"
                )

        text = text or ""
        return {
            "status": "ok",
            "text": text,
            "sections": segment_resume(text),
            "source": source,
            "length": len(text),
            "truncated": False,
        }

    @staticmethod
    def _error_result(source: str, error: object) -> dict:
        return {"status": "error", "text": "", "source": source, "error": str(error)}

    @staticmethod
    def _check_response(payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise MinerUParseError("MinerU API 返回不是 JSON 对象")
        if payload.get("code") not in (0, "0"):
            raise MinerUParseError(
                payload.get("msg") or f"MinerU API code={payload.get('code')}"
            )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise MinerUParseError("MinerU API 返回缺少 data")
        return data

    def _api_headers(self) -> dict:
        if not self.api_token:
            raise MinerUParseError("未配置 MINERU_API_TOKEN")
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _parse_with_mineru_api(self, pdf_bytes: bytes, filename: str) -> str:
        """Submit, upload, poll and download through MinerU precision API."""
        if len(pdf_bytes) > self.MAX_PRECISION_BYTES:
            raise MinerUParseError("PDF 超过 MinerU 精准 API 的 200MB 限制")

        data_id = f"resume-{uuid.uuid4().hex}"
        payload = {
            "files": [{
                "name": filename,
                "data_id": data_id,
                "is_ocr": self._env_bool("MINERU_IS_OCR", False),
            }],
            "model_version": self.model_version,
            "language": self.language,
            "enable_table": self._env_bool("MINERU_ENABLE_TABLE", True),
            "enable_formula": self._env_bool("MINERU_ENABLE_FORMULA", True),
        }
        page_ranges = os.getenv("MINERU_PAGE_RANGES", "").strip()
        if page_ranges:
            payload["files"][0]["page_ranges"] = page_ranges

        submit = requests.post(
            f"{self.api_base_url}/file-urls/batch",
            headers=self._api_headers(),
            json=payload,
            timeout=self.request_timeout,
        )
        submit.raise_for_status()
        submit_data = self._check_response(submit.json())
        batch_id = submit_data.get("batch_id")
        upload_urls = submit_data.get("file_urls") or []
        if not batch_id or not upload_urls:
            raise MinerUParseError("MinerU API 未返回 batch_id 或 file_urls")

        upload = requests.put(upload_urls[0], data=pdf_bytes, timeout=self.request_timeout)
        upload.raise_for_status()

        deadline = time.monotonic() + self.poll_timeout
        while time.monotonic() < deadline:
            response = requests.get(
                f"{self.api_base_url}/extract-results/batch/{batch_id}",
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            data = self._check_response(response.json())
            file_result = self._find_file_result(data, filename)
            if file_result is None:
                time.sleep(self.poll_interval)
                continue

            state = file_result.get("state")
            if state == "done":
                zip_url = file_result.get("full_zip_url")
                if not zip_url:
                    raise MinerUParseError("MinerU 任务完成但未返回 full_zip_url")
                return self._download_full_markdown(zip_url)
            if state == "failed":
                raise MinerUParseError(
                    file_result.get("err_msg") or "MinerU 任务解析失败"
                )
            time.sleep(self.poll_interval)

        raise MinerUParseError(f"MinerU 批次轮询超时: batch_id={batch_id}")

    @staticmethod
    def _find_file_result(data: dict, filename: str) -> dict | None:
        results = data.get("extract_result") or []
        if isinstance(results, dict):
            results = [results]
        if not isinstance(results, list):
            return None
        for item in results:
            if isinstance(item, dict) and item.get("file_name") == filename:
                return item
        return results[0] if results and isinstance(results[0], dict) else None

    def _download_full_markdown(self, zip_url: str) -> str:
        archive = requests.get(zip_url, timeout=self.request_timeout)
        archive.raise_for_status()
        with zipfile.ZipFile(BytesIO(archive.content)) as zip_file:
            markdown_name = next(
                (name for name in zip_file.namelist() if Path(name).name == "full.md"),
                None,
            )
            if not markdown_name:
                raise MinerUParseError("MinerU 结果 ZIP 中未找到 full.md")
            return zip_file.read(markdown_name).decode("utf-8-sig")

    def _parse_with_pypdf(self, pdf_bytes: bytes) -> str:
        """Fallback parser for API outages or invalid API configuration."""
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)


parser = ResumeParser()


@tool
def parse_resume_pdf(pdf_bytes_b64: str) -> str:
    """Parse a base64-encoded resume PDF and return structured parsing output."""
    pdf_bytes = base64.b64decode(pdf_bytes_b64)
    result = parser.parse(pdf_bytes)
    return json.dumps(result, ensure_ascii=False)
