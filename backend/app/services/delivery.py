from __future__ import annotations

from pathlib import Path
import smtplib
import asyncio
from email.message import EmailMessage

from telegram import Bot

from app.config import settings


def deliver_telegram(pdf_path: str, caption: str = "Resumo diário de notícias") -> str:
    """Envia PDF para Telegram usando bot token + chat id via env.

    Returns: status string para logging.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return "telegram_skipped_missing_config"

    p = Path(pdf_path)
    if not p.exists():
        return f"telegram_skipped_missing_file:{pdf_path}"

    bot = Bot(token=settings.telegram_bot_token)

    async def _send() -> None:
        with p.open("rb") as f:
            await bot.send_document(
                chat_id=settings.telegram_chat_id,
                document=f,
                filename=p.name,
                caption=caption,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=20,
                pool_timeout=20,
            )

    asyncio.run(_send())
    return "telegram_sent"


def deliver_email(html_path: str, pdf_path: str, subject: str = "Resumo diário de notícias") -> str:
    """SMTP real, porém controlado por SMTP_ENABLED."""
    if not settings.smtp_enabled:
        return "smtp_disabled"

    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_to]):
        return "smtp_skipped_missing_config"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = settings.smtp_to

    body_html = Path(html_path).read_text(encoding="utf-8") if Path(html_path).exists() else ""
    msg.set_content("Segue em anexo o resumo diário de notícias.")
    msg.add_alternative(body_html or "<p>Segue em anexo o resumo diário de notícias.</p>", subtype="html")

    pdf_bytes = Path(pdf_path).read_bytes()
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=Path(pdf_path).name)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    return "smtp_sent"
