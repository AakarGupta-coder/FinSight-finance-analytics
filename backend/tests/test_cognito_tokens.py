"""Cognito access-token verification (AUTH_MODE=cognito) with a local RSA key standing in for the pool JWKS."""

import dataclasses
import datetime as dt

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import tokens
from app.errors import Unauthorized

POOL_ID = "ap-south-1_TestPool1"
CLIENT_ID = "testclientid123"


@pytest.fixture
def cognito_settings(settings):
    return dataclasses.replace(settings, auth_mode="cognito", cognito_user_pool_id=POOL_ID,
                               cognito_app_client_id=CLIENT_ID)


@pytest.fixture
def private_key(monkeypatch, cognito_settings):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class StubJwks:
        def get_signing_key_from_jwt(self, token):
            return jwt.PyJWK.from_dict(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True) | {"alg": "RS256"})

    monkeypatch.setitem(tokens._jwks_clients, cognito_settings.cognito_issuer, StubJwks())
    monkeypatch.setattr(tokens, "_revocation_checked", {})
    return key


class StubCognito:
    """Stands in for cognito-idp GetUser: revoked tokens raise NotAuthorizedException."""

    def __init__(self, error_code=None):
        self.calls = 0
        self.error_code = error_code

    def get_user(self, AccessToken):  # noqa: N803 - boto3 parameter name
        self.calls += 1
        if self.error_code:
            exc = Exception(self.error_code)
            exc.response = {"Error": {"Code": self.error_code}}
            raise exc
        return {"Username": "x"}


@pytest.fixture
def cognito_api(monkeypatch):
    stub = StubCognito()
    monkeypatch.setattr(tokens, "_cognito_client", lambda region: stub)
    return stub


def _token(key, settings, **overrides):
    now = dt.datetime.now(dt.UTC)
    claims = {"sub": "4f1c2b7e-0000-4000-8000-000000000001", "iss": settings.cognito_issuer, "token_use": "access",
              "client_id": CLIENT_ID, "username": "4f1c2b7e-0000-4000-8000-000000000001",
              "iat": now, "exp": now + dt.timedelta(minutes=60)}
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="RS256")


def test_valid_access_token_uses_sub_and_no_uuid_display_name(cognito_settings, private_key, cognito_api):
    user = tokens.verify_token(cognito_settings, _token(private_key, cognito_settings))
    assert user.id == "4f1c2b7e-0000-4000-8000-000000000001"
    # The username claim is an opaque UUID when email is the sign-in alias; it must not become the name.
    assert user.name == ""


@pytest.mark.parametrize("overrides", [
    {"token_use": "id"},
    {"client_id": "some-other-client"},
    {"iss": "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_OtherPool"},
])
def test_wrong_token_type_client_or_issuer_rejected(cognito_settings, private_key, cognito_api, overrides):
    with pytest.raises(Unauthorized):
        tokens.verify_token(cognito_settings, _token(private_key, cognito_settings, **overrides))


def test_expired_token_rejected_with_expiry_code(cognito_settings, private_key, cognito_api):
    past = dt.datetime.now(dt.UTC) - dt.timedelta(hours=2)
    with pytest.raises(Unauthorized) as exc:
        tokens.verify_token(cognito_settings, _token(private_key, cognito_settings, iat=past,
                                                     exp=past + dt.timedelta(minutes=60)))
    assert exc.value.code == "token_expired"


def test_token_signed_by_another_key_rejected(cognito_settings, private_key, cognito_api):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(Unauthorized):
        tokens.verify_token(cognito_settings, _token(other, cognito_settings))


def test_revoked_token_rejected_after_sign_out(cognito_settings, private_key, cognito_api):
    token = _token(private_key, cognito_settings, jti="jti-revoked")
    cognito_api.error_code = "NotAuthorizedException"  # what GetUser returns after GlobalSignOut
    with pytest.raises(Unauthorized) as exc:
        tokens.verify_token(cognito_settings, token)
    assert exc.value.code == "token_revoked"


def test_revocation_check_is_cached_briefly(cognito_settings, private_key, cognito_api):
    token = _token(private_key, cognito_settings, jti="jti-cached")
    tokens.verify_token(cognito_settings, token)
    tokens.verify_token(cognito_settings, token)
    assert cognito_api.calls == 1
    no_cache = dataclasses.replace(cognito_settings, token_check_cache_seconds=0)
    tokens.verify_token(no_cache, token)
    assert cognito_api.calls == 2


def test_revocation_check_fails_open_on_throttling(cognito_settings, private_key, cognito_api):
    cognito_api.error_code = "TooManyRequestsException"
    user = tokens.verify_token(cognito_settings, _token(private_key, cognito_settings, jti="jti-throttled"))
    assert user.id.startswith("4f1c2b7e")


def test_revocation_check_can_be_disabled(cognito_settings, private_key, cognito_api):
    off = dataclasses.replace(cognito_settings, cognito_revocation_check=False)
    tokens.verify_token(off, _token(private_key, cognito_settings, jti="jti-off"))
    assert cognito_api.calls == 0
