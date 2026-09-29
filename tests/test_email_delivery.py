import logging
import sys
import types
import unittest
from unittest.mock import patch

import email_delivery
try:
    import requests
except ModuleNotFoundError:
    sys.modules["requests"] = types.ModuleType("requests")
import pubmed_monitor


ARTICLE = {
    "pmid": "123",
    "title": "A < B & C",
    "journal_abbr": "Test Journal",
    "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
    "abstract": "Example abstract",
}
GROUPS = {"研究": [ARTICLE]}


class EmailDeliveryTests(unittest.TestCase):
    def test_email_contains_links_and_escapes_html(self):
        message = email_delivery.build_email(GROUPS, "Summary <draft>", 1, "sender@qq.com", "reader@example.com")
        plain = message.get_body(preferencelist=("plain",)).get_content()
        html = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn(ARTICLE["url"], plain)
        self.assertIn('href="https://pubmed.ncbi.nlm.nih.gov/123/"', html)
        self.assertIn("A &lt; B &amp; C", html)
        self.assertIn("Summary &lt;draft&gt;", html)

    @patch("email_delivery.smtplib.SMTP_SSL")
    def test_successful_send_uses_qq_smtp(self, smtp_ssl):
        config = {"qq_email_sender": "sender@qq.com", "qq_email_auth_code": "TEST_ONLY", "email_recipient": "reader@example.com"}
        result = email_delivery.send_email(GROUPS, "Summary", 1, config, logging.getLogger("test"))
        self.assertTrue(result)
        smtp_ssl.assert_called_once_with("smtp.qq.com", 465, timeout=30)
        smtp = smtp_ssl.return_value.__enter__.return_value
        smtp.login.assert_called_once_with("sender@qq.com", "TEST_ONLY")
        smtp.send_message.assert_called_once()

    @patch.object(pubmed_monitor, "save_seen")
    @patch.object(pubmed_monitor, "send_email", return_value=False)
    @patch.object(pubmed_monitor, "ai_summarize", return_value="Summary")
    @patch.object(pubmed_monitor, "is_research_article", return_value=True)
    @patch.object(pubmed_monitor, "fetch_articles", return_value=[ARTICLE])
    @patch.object(pubmed_monitor, "search_journal", return_value=["123"])
    @patch.object(pubmed_monitor, "load_seen", return_value={})
    @patch.object(pubmed_monitor.time, "sleep")
    def test_failed_send_does_not_mark_papers_seen(self, _sleep, _load, _search, _fetch, _filter, _summarize, _send, save_seen):
        config = {"journals": {"研究": ["Test Journal"]}}
        with self.assertRaisesRegex(RuntimeError, "邮件推送失败"):
            pubmed_monitor.run_once(config, logging.getLogger("test"))
        save_seen.assert_not_called()

    @patch.object(pubmed_monitor, "save_seen")
    @patch.object(pubmed_monitor, "send_email", return_value=True)
    @patch.object(pubmed_monitor, "ai_summarize", return_value="Summary")
    @patch.object(pubmed_monitor, "is_research_article", return_value=True)
    @patch.object(pubmed_monitor, "fetch_articles", return_value=[ARTICLE])
    @patch.object(pubmed_monitor, "search_journal", return_value=["123"])
    @patch.object(pubmed_monitor, "load_seen", return_value={"123": {"pushed": False}})
    @patch.object(pubmed_monitor.time, "sleep")
    def test_previous_failed_delivery_is_retried(self, _sleep, _load, _search, _fetch, _filter, _summarize, send, save_seen):
        pubmed_monitor.run_once({"journals": {"研究": ["Test Journal"]}}, logging.getLogger("test"))
        send.assert_called_once()
        self.assertTrue(save_seen.call_args.args[1]["123"]["pushed"])


if __name__ == "__main__":
    unittest.main()
