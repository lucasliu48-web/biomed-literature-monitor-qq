import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import send_analysis_digest


class AnalysisDigestTests(unittest.TestCase):
    def test_email_escapes_source_content_and_marks_missing_abstract(self):
        entries = {
            "123": {
                "title_zh": "研究 <A>",
                "abstract_zh": "发现 & 结果",
                "analysis_zh": "仍需 <验证>",
            },
            "456": {"title_zh": "仅有标题"},
        }
        message = send_analysis_digest.build_email("2026-09-30", entries, "sender@qq.com", "reader@qq.com")
        html = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn("研究 &lt;A&gt;", html)
        self.assertIn("发现 &amp; 结果", html)
        self.assertIn("仍需 &lt;验证&gt;", html)
        self.assertIn("PubMed 无摘要：仅翻译标题", html)
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/123/", html)

    @patch("send_analysis_digest.smtplib.SMTP_SSL")
    def test_sends_once_and_records_date(self, smtp_ssl):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "analysis"
            directory.mkdir()
            (directory / "2026-09-30.json").write_text(
                json.dumps({"123": {"title_zh": "中文标题", "abstract_zh": "摘要", "analysis_zh": "解读"}}),
                encoding="utf-8",
            )
            state = Path(tmp) / "analysis_sent.json"
            with patch.object(send_analysis_digest, "ANALYSIS_DIR", directory), patch.object(
                send_analysis_digest, "SENT_FILE", state
            ), patch.dict(
                send_analysis_digest.os.environ,
                {
                    "QQ_EMAIL_SENDER": "sender@qq.com",
                    "QQ_EMAIL_AUTH_CODE": "TEST_ONLY",
                    "EMAIL_RECIPIENT": "reader@qq.com",
                },
            ), patch.object(sys, "argv", ["send_analysis_digest.py"]):
                send_analysis_digest.main()
                send_analysis_digest.main()
            smtp_ssl.assert_called_once_with("smtp.qq.com", 465, timeout=30)
            smtp_ssl.return_value.__enter__.return_value.send_message.assert_called_once()
            self.assertIn("2026-09-30", json.loads(state.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
