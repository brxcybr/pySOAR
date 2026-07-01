"""Webhook notification integration."""

import json

import requests

from classes import Log


class WebhookFunction:
    """Send playbook notifications to generic, Slack, or Discord webhooks."""

    def __init__(self, webhook_init):
        self.log = Log.get_instance()
        self.url = webhook_init.url
        self.api_key = webhook_init.api_key
        self.ssl = webhook_init.ssl
        self.verifycert = webhook_init.verifycert
        self.default_format = getattr(webhook_init, 'default_format', 'generic')
        if hasattr(webhook_init, 'params'):
            cfg = webhook_init.params.get('webhook', {})
            self.default_format = cfg.get('default_format', self.default_format)

    def _session(self):
        session = requests.Session()
        session.verify = self.verifycert if self.ssl else False
        if self.api_key:
            session.headers['Authorization'] = f"Bearer {self.api_key}"
        session.headers['Content-Type'] = 'application/json'
        return session

    def send_webhook(self, url=None, payload=None, message=None, **kwargs):
        target = url or self.url
        body = payload or {"message": message or "PySOAR notification", **kwargs}
        response = self._session().post(target, data=json.dumps(body), timeout=30)
        self.log.info(f"Webhook sent to {target}: HTTP {response.status_code}")
        return {
            "webhook-status": response.ok,
            "webhook-response": response.text[:500],
        }

    def send_slack_message(self, message, webhook_url=None, **kwargs):
        target = webhook_url or self.url
        payload = {"text": message, **kwargs}
        return self.send_webhook(url=target, payload=payload)

    def send_discord_message(self, message, webhook_url=None, username="PySOAR", **kwargs):
        target = webhook_url or self.url
        payload = {"content": message, "username": username, **kwargs}
        return self.send_webhook(url=target, payload=payload)

    def notify_playbook_result(self, playbook_name=None, message=None, ip_dst=None, success=True):
        text = message or (
            f"Playbook '{playbook_name}' completed. Success={success}. Indicators={ip_dst}"
        )
        if self.default_format == "slack":
            return self.send_slack_message(text)
        if self.default_format == "discord":
            return self.send_discord_message(text)
        return self.send_webhook(
            payload={
                "playbook": playbook_name,
                "success": success,
                "ip-dst": ip_dst,
                "message": text,
            }
        )
