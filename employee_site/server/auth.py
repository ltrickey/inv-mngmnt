"""Cognito JWT validation middleware for Flask."""

import json
import os
import time
import urllib.request
from functools import wraps

import jwt
from flask import request, jsonify, g

COGNITO_REGION = os.environ.get("AWS_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID", "")
SKIP_AUTH = os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes")

_auth_configured = bool(COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID)

if not SKIP_AUTH and not _auth_configured:
    raise RuntimeError(
        "Cognito is not configured (COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID are required). "
        "Set SKIP_AUTH=1 for local development only."
    )

if SKIP_AUTH and _auth_configured:
    import logging as _log
    _log.getLogger(__name__).warning(
        "SKIP_AUTH is enabled but Cognito IS configured -- "
        "auth will be SKIPPED. Do NOT deploy like this."
    )

_jwks_cache = {"keys": None, "fetched_at": 0}
JWKS_CACHE_TTL = 3600  # seconds


def _get_jwks():
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < JWKS_CACHE_TTL:
        return _jwks_cache["keys"]

    url = (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read())

    _jwks_cache["keys"] = {k["kid"]: k for k in data["keys"]}
    _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


def _decode_token(token: str) -> dict:
    """Decode and verify a Cognito ID token."""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = _get_jwks()

    if kid not in jwks:
        raise ValueError("Token signed with unknown key")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwks[kid])
    issuer = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=COGNITO_APP_CLIENT_ID,
        issuer=issuer,
    )


def require_auth(f):
    """Decorator that validates Cognito JWT before allowing access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if SKIP_AUTH:
            g.user = {"sub": "local-dev", "email": "dev@localhost"}
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[len("Bearer "):]
        try:
            claims = _decode_token(token)
        except Exception as e:
            return jsonify({"error": f"Token validation failed: {e}"}), 401

        g.user = claims
        return f(*args, **kwargs)

    return decorated
