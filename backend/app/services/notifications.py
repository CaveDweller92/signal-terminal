"""
Notification service — sends email alerts via Resend.

Used for:
- Morning watchlist email (6:00 AM)
- CRITICAL/HIGH exit alerts
- Daily performance review (4:15 PM)

Falls back to logging when Resend API key is not configured.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self._resend_available = bool(settings.resend_api_key and settings.alert_email)

    async def send_watchlist_email(self, picks: list[dict]) -> bool:
        """Send the morning watchlist email."""
        subject = f"Signal Terminal — Today's Watchlist ({len(picks)} picks)"
        body = self._format_watchlist(picks)
        return await self._send_email(subject, body)

    async def send_exit_alert(self, signal: dict, position: dict) -> bool:
        """Send an exit alert email for CRITICAL/HIGH urgency."""
        subject = f"EXIT ALERT: {signal['symbol']} — {signal['exit_type'].replace('_', ' ').upper()}"
        body = (
            f"<h2>{signal['message']}</h2>"
            f"<p>Current Price: ${signal['current_price']:.2f}</p>"
            f"<p>Urgency: <strong>{signal['urgency'].upper()}</strong></p>"
            f"<p>Position: {position.get('direction', 'N/A')} "
            f"{position.get('quantity', 0)} shares @ ${position.get('entry_price', 0):.2f}</p>"
        )
        return await self._send_email(subject, body)

    async def send_daily_review(self, review: dict) -> bool:
        """Send the daily performance review email."""
        subject = "Signal Terminal — Daily Performance Review"
        body = (
            f"<h2>Daily Review</h2>"
            f"<p>{review.get('summary', 'No summary available')}</p>"
            f"<h3>Recommendations</h3>"
            f"<ul>{''.join(f'<li>{r}</li>' for r in review.get('recommendations', []))}</ul>"
        )
        return await self._send_email(subject, body)

    async def _send_email(self, subject: str, html_body: str) -> bool:
        if not self._resend_available:
            logger.info(f"[Email skipped — no Resend key] {subject}")
            return False

        try:
            import resend
            resend.api_key = settings.resend_api_key

            resend.Emails.send({
                "from": "Signal Terminal <signals@resend.dev>",
                "to": [settings.alert_email],
                "subject": subject,
                "html": html_body,
            })
            logger.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Email failed: {e}")
            return False

    def _format_watchlist(self, picks: list[dict]) -> str:
        rows = ""
        for i, pick in enumerate(picks, 1):
            rows += (
                f"<tr>"
                f"<td>{i}</td>"
                f"<td><strong>{pick.get('symbol', 'N/A')}</strong></td>"
                f"<td>{pick.get('sector', 'N/A')}</td>"
                f"<td>{pick.get('reasoning', 'N/A')}</td>"
                f"</tr>"
            )
        return (
            f"<h2>Today's Watchlist</h2>"
            f"<table border='1' cellpadding='8'>"
            f"<tr><th>#</th><th>Symbol</th><th>Sector</th><th>Reasoning</th></tr>"
            f"{rows}</table>"
        )
