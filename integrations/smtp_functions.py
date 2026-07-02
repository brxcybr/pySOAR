"""SMTP email notification integration (stdlib only)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from classes import Log
from integrations.base import IntegrationBase, use_mock_mode


class SmtpFunction(IntegrationBase):
    """Send email notifications through any SMTP relay."""

    integration_name = 'smtp'

    def __init__(self, smtp_init):
        super().__init__(smtp_init)
        self.log = Log.get_instance()
        self.url = smtp_init.url  # host or host:port
        self.api_key = smtp_init.api_key  # SMTP password (optional)
        self.ssl = smtp_init.ssl
        params = getattr(smtp_init, 'params', {}) or {}
        cfg = params.get('smtp', {}) if isinstance(params, dict) else {}
        self.username = cfg.get('username', '')
        self.from_addr = cfg.get('from_addr', 'pysoar@localhost')
        self.to_addrs = cfg.get('to_addrs', [])
        self.starttls = bool(cfg.get('starttls', True))
        self._mock = use_mock_mode(smtp_init)

    def _host_port(self):
        raw = (self.url or 'localhost').replace('smtp://', '').rstrip('/')
        if ':' in raw:
            host, _, port = raw.rpartition(':')
            return host, int(port)
        return raw, 587 if self.starttls else 25

    def send_email(self, subject=None, message=None, recipients=None, **kwargs):
        """Send a notification email. Returns a status dict."""
        to_addrs = recipients or self.to_addrs
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        if not to_addrs:
            self.log.error('SMTP notifier has no recipients configured.')
            return {'email-status': False, 'email-error': 'no recipients'}

        subject = subject or 'PySOAR notification'
        body = message or 'PySOAR playbook notification.'

        if self.mock_mode or self._mock:
            self.log.info(f"[mock] email to {to_addrs}: {subject}")
            return {'email-status': True, 'email-recipients': to_addrs, 'mock': True}

        email = EmailMessage()
        email['Subject'] = subject
        email['From'] = self.from_addr
        email['To'] = ', '.join(to_addrs)
        email.set_content(body)

        host, port = self._host_port()
        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if self.starttls:
                    server.starttls()
                if self.username and self.api_key:
                    server.login(self.username, self.api_key)
                server.send_message(email)
            self.log.info(f'Email notification sent to {to_addrs}')
            return {'email-status': True, 'email-recipients': to_addrs}
        except Exception as exc:
            self.log.error(f'SMTP send failed: {exc}')
            return {'email-status': False, 'email-error': str(exc)}

    def notify_playbook_result(self, playbook_name=None, message=None, ip_dst=None, success=True):
        subject = f"PySOAR: playbook '{playbook_name}' {'completed' if success else 'FAILED'}"
        body = message or (
            f"Playbook: {playbook_name}\n"
            f"Success: {success}\n"
            f"Indicators: {ip_dst}\n"
        )
        return self.send_email(subject=subject, message=body)
