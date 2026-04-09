from ibms_core.security.jwt_auth import decode_token, issue_token, validate_token


def test_issue_and_validate_token_round_trip():
    token = issue_token("alice@example.com", "secret-1", ttl_seconds=3600)
    assert validate_token(token, "secret-1") is True


def test_decode_token_contains_subject_and_type():
    token = issue_token("bob@example.com", "secret-2", ttl_seconds=3600, token_type="access")
    payload = decode_token(token, "secret-2")
    assert payload["sub"] == "bob@example.com"
    assert payload["token_type"] == "access"


def test_validate_token_fails_with_wrong_secret():
    token = issue_token("eve@example.com", "good-secret", ttl_seconds=3600)
    assert validate_token(token, "bad-secret") is False
