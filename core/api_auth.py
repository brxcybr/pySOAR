"""REST API token authentication."""

import os
import secrets
from typing import Optional


def api_auth_enabled() -> bool:
    return bool(os.environ.get('PYSOAR_API_TOKEN', '').strip())


def expected_api_token() -> Optional[str]:
    token = os.environ.get('PYSOAR_API_TOKEN', '').strip()
    return token or None


def verify_api_token(authorization: Optional[str]) -> bool:
    expected = expected_api_token()
    if not expected:
        return True
    if not authorization:
        return False
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer':
        return False
    return secrets.compare_digest(token.strip(), expected)
