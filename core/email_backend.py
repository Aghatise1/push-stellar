"""HTTPS transactional email transport for hosts that block SMTP ports."""

import json
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    endpoint = 'https://api.brevo.com/v3/smtp/email'

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            sender_name, sender_email = parseaddr(message.from_email)
            if not sender_email or not message.to:
                if self.fail_silently:
                    continue
                raise ValueError('A verified sender and recipient are required.')
            payload = {
                'sender': {'name': sender_name or 'Push', 'email': sender_email},
                'to': [{'email': address} for address in message.to],
                'subject': message.subject,
                'textContent': message.body,
            }
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'api-key': settings.PUSH_BREVO_API_KEY,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                method='POST',
            )
            try:
                with urlopen(request, timeout=12) as response:
                    if response.status not in (200, 201, 202):
                        raise RuntimeError(f'Email provider returned HTTP {response.status}.')
            except (HTTPError, URLError, TimeoutError, RuntimeError):
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent
