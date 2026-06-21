from __future__ import annotations

import os
import re
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path


BRIEF_FILE = Path("daily_brief.md")


def env_value(name: str, default: str | None = None) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        if default is not None:
            return default
        raise RuntimeError(f"缺少必要環境變數：{name}")
    return value.strip()


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def subject_from_brief(content: str) -> str:
    first_line = content.splitlines()[0] if content.splitlines() else ""
    match = re.match(r"#\s*Daily Research Brief\s*-\s*(\d{4}-\d{2}-\d{2})", first_line)
    if match:
        return f"Daily Research Brief - {match.group(1)}"
    return "Daily Research Brief"


def send_email() -> None:
    if not BRIEF_FILE.exists():
        raise RuntimeError(f"找不到 {BRIEF_FILE}，請先執行 fetch_news.py")

    brief_content = BRIEF_FILE.read_text(encoding="utf-8")
    smtp_host = env_value("SMTP_HOST")
    smtp_port = int(env_value("SMTP_PORT", "587"))
    smtp_username = env_value("SMTP_USERNAME")
    smtp_password = env_value("SMTP_PASSWORD")
    email_from = env_value("EMAIL_FROM", smtp_username)
    email_to = env_value("EMAIL_TO")
    use_ssl = env_bool("SMTP_USE_SSL", smtp_port == 465)
    use_starttls = env_bool("SMTP_USE_STARTTLS", not use_ssl)

    message = EmailMessage()
    message["Subject"] = subject_from_brief(brief_content)
    message["From"] = email_from
    message["To"] = email_to
    message.set_content(brief_content)

    recipients = [address.strip() for address in email_to.split(",") if address.strip()]
    if not recipients:
        raise RuntimeError("EMAIL_TO 未提供有效收件人")

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message, to_addrs=recipients)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            if use_starttls:
                smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message, to_addrs=recipients)

    print(f"已寄出 daily_brief.md 至 {', '.join(recipients)}")


def main() -> int:
    try:
        send_email()
    except Exception as exc:
        print(f"寄送 Email 失敗：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
