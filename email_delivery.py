"""Send a PubMed briefing through QQ Mail."""

import html
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage


def build_email(articles_by_group, summary, total_count, sender, recipient):
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"生物医药顶刊文献速递 | {today} | {total_count} 篇新文献"
    plain = [subject, "", "文献摘要：", summary, "", "文献列表："]
    sections = []
    for group, articles in articles_by_group.items():
        if not articles:
            continue
        plain.append(f"\n{group}")
        items = []
        for art in articles:
            plain.append(f"- {art['title']} ({art['journal_abbr']})\n  {art['url']}")
            items.append(
                f'<li><a href="{html.escape(art["url"], quote=True)}">'
                f'{html.escape(art["title"])}</a> '
                f'<small>{html.escape(art["journal_abbr"])}</small></li>'
            )
        sections.append(f"<h2>{html.escape(group)}</h2><ul>{''.join(items)}</ul>")

    html_body = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<body style="font-family:Arial,sans-serif;max-width:720px;margin:auto;line-height:1.6">'
        f'<h1>{html.escape(subject)}</h1>'
        f'<p>发现 {total_count} 篇新文献。数据来源：PubMed。</p>'
        f'<h2>文献摘要</h2><div style="white-space:pre-wrap">{html.escape(summary)}</div>'
        f'<h2>文献列表</h2>{"".join(sections)}'
        '</body></html>'
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(plain))
    message.add_alternative(html_body, subtype="html")
    return message


def send_email(articles_by_group, summary, total_count, config, logger: logging.Logger):
    sender = config.get("qq_email_sender", "").strip()
    auth_code = config.get("qq_email_auth_code", "").strip()
    recipient = config.get("email_recipient", "").strip()
    if not sender or not auth_code or not recipient:
        logger.error("邮件配置不完整：需配置发件邮箱、QQ 邮箱授权码和收件邮箱")
        return False
    try:
        message = build_email(articles_by_group, summary, total_count, sender, recipient)
        with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30) as smtp:
            smtp.login(sender, auth_code)
            smtp.send_message(message)
        logger.info("QQ 邮箱推送成功，共 %s 篇文献", total_count)
        return True
    except (OSError, smtplib.SMTPException) as error:
        logger.error("QQ 邮箱推送失败（%s）", type(error).__name__)
        return False
