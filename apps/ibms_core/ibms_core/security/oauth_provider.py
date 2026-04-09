def get_oauth_provider_config():
    return {
        "provider": "IBMS OAuth2",
        "authorization_url": "/api/method/ibms_core.api.auth.authorize",
        "token_url": "/api/method/ibms_core.api.auth.token",
        "scopes": ["openid", "profile", "erp.read", "erp.write"],
    }
