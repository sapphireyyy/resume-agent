"""
简历 PDF 解析 Skill — MinerU 将 PDF 转结构化文本
"""
import os
import json
import tempfile
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from logger_config import setup_logger

logger = setup_logger("skills.parse_resume")


class ResumeParser:
    """简历 PDF → 纯文本，支持 MinerU / 降级 PyPDF"""

    def parse(self, pdf_bytes: bytes, filename: str = "resume.pdf") -> dict:
        try:
            logger.info("使用 PyPDF2 提取 PDF 文本...")
            text = self._parse_with_pypdf(pdf_bytes)
            source = "pypdf"
            logger.info(f"PyPDF2 解析成功, 文本长度={len(text)}")
        except Exception:
            logger.warning("PyPDF2 失败, 尝试降级 MinerU")
            # 写入临时文件
            tmp_dir = tempfile.mkdtemp()
            pdf_path = os.path.join(tmp_dir, filename)
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            try:
                text = self._parse_with_mineru(pdf_path)
                source = "mineru"
                logger.info(f"MinerU 解析成功, 文本长度={len(text)}")
            except Exception as e:
                logger.error(f"PDF 解析完全失败: {e}")
                return {"status": "error", "text": "", "source": "none", "error": str(e)}
            finally:
                for f in Path(tmp_dir).glob("*"):
                    f.unlink()
                os.rmdir(tmp_dir)

        return {"status": "ok", "text": text[:8000], "source": source, "length": len(text)}

    def _parse_with_mineru(self, pdf_path: str) -> str:
        """MinerU CLI 解析"""
        output_dir = os.path.join(os.path.dirname(pdf_path), "mineru_output")
        result = subprocess.run(
            ["magic-pdf", "-p", pdf_path, "-o", output_dir],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        # MinerU 输出目录下找 markdown 文件
        for root, _, files in os.walk(output_dir):
            for f in files:
                if f.endswith(".md"):
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                        return fp.read()
        raise FileNotFoundError("MinerU 未生成 Markdown")

    def _parse_with_pypdf(self, pdf_bytes: bytes) -> str:
        """降级方案：PyPDF 提取"""
        from io import BytesIO
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages)


parser = ResumeParser()


@tool
def parse_resume_pdf(pdf_bytes_b64: str) -> str:
    """解析简历 PDF 为纯文本。传入 base64 编码的 PDF 内容，返回解析后的文本。"""
    import base64
    pdf_bytes = base64.b64decode(pdf_bytes_b64)
    result = parser.parse(pdf_bytes)
    return json.dumps(result, ensure_ascii=False)
