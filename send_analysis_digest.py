"""Send a manually prepared Chinese literature digest through QQ Mail."""

import argparse
import html
import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ANALYSIS_DIR = ROOT / "analysis"
SENT_FILE = ROOT / "analysis_sent.json"


def latest_digest():
    files = sorted(ANALYSIS_DIR.glob("????-??-??.json"))
    if not files:
        raise RuntimeError("analysis 文件夹中没有日期命名的解读文件")
    path = files[-1]
    date = path.stem
    datetime.strptime(date, "%Y-%m-%d")
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, dict) or not entries:
        raise ValueError("解读文件必须是包含文献的 JSON 对象")
    for pmid, item in entries.items():
        if not pmid.isdigit() or not isinstance(item, dict) or not item.get("title_zh"):
            raise ValueError("解读文件包含无效 PMID 或缺少中文标题")
        if bool(item.get("abstract_zh")) != bool(item.get("analysis_zh")):
            raise ValueError("摘要译述与解读必须同时填写")
    return date, entries


def build_email(date, entries, sender, recipient):
    total = len(entries)
    interpreted = sum(bool(item.get("abstract_zh") and item.get("analysis_zh")) for item in entries.values())
    subject = f"生物医药文献中文解读 | {date} | {total} 篇"
    note = f"共 {total} 篇：{interpreted} 篇含摘要译述与解读，其余仅翻译标题。内容依据 PubMed 摘要，未核对全文。"
    plain = [subject, note]
    cards = []
    for index, (pmid, item) in enumerate(entries.items(), 1):
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        title = str(item["title_zh"])
        kind = str(item.get("kind", ""))
        summary = str(item.get("abstract_zh", ""))
        analysis = str(item.get("analysis_zh", ""))
        plain.extend(["", f"{index}. {title}", kind, f"PubMed：{url}"])
        if summary and analysis:
            plain.extend([f"摘要中文译述：{summary}", f"Codex 解读与局限：{analysis}"])
        else:
            plain.append("PubMed 无摘要：仅翻译标题，未生成研究结论。")
        detail = (
            f'<p><b>摘要中文译述：</b>{html.escape(summary)}</p>'
            f'<p><b>Codex 解读与局限：</b>{html.escape(analysis)}</p>'
            if summary and analysis
            else "<p>PubMed 无摘要：仅翻译标题，未生成研究结论。</p>"
        )
        cards.append(
            '<section style="border-top:1px solid #dce5ed;padding:16px 0">'
            f'<h2 style="font-size:18px;margin:0 0 6px">{index}. {html.escape(title)}</h2>'
            f'<p style="color:#60758a;margin:0 0 8px">{html.escape(kind)} · '
            f'<a href="{url}">PubMed PMID {pmid}</a></p>{detail}</section>'
        )
    body = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<body style="font-family:Arial,sans-serif;max-width:760px;margin:auto;line-height:1.65;color:#1b2b42">'
        f'<h1>{html.escape(subject)}</h1><p>{html.escape(note)}</p>'
        f'{"".join(cards)}</body></html>'
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(plain))
    message.add_alternative(body, subtype="html")
    return message


def main():
    parser = argparse.ArgumentParser(description="发送人工审核的中文文献解读")
    parser.add_argument("--dry-run", action="store_true", help="只验证并输出篇数，不发送")
    args = parser.parse_args()
    date, entries = latest_digest()
    sent = json.loads(SENT_FILE.read_text(encoding="utf-8")) if SENT_FILE.exists() else {}
    if date in sent:
        print(f"{date} 的中文解读已发送，跳过")
        return
    if args.dry_run:
        print(f"{date}: {len(entries)} 篇，{sum(bool(x.get('analysis_zh')) for x in entries.values())} 篇有解读；未发送")
        return
    sender = os.environ.get("QQ_EMAIL_SENDER", "").strip()
    auth_code = os.environ.get("QQ_EMAIL_AUTH_CODE", "").strip()
    recipient = os.environ.get("EMAIL_RECIPIENT", "").strip()
    if not all((sender, auth_code, recipient)):
        raise RuntimeError("缺少 QQ 邮箱 Secrets：发件邮箱、授权码或收件邮箱")
    message = build_email(date, entries, sender, recipient)
    with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30) as smtp:
        smtp.login(sender, auth_code)
        smtp.send_message(message)
    sent[date] = datetime.now(timezone.utc).isoformat()
    SENT_FILE.write_text(json.dumps(sent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{date} 的中文解读已发送，共 {len(entries)} 篇")


if __name__ == "__main__":
    main()
