"""Keycloak authentication adapter for the production candidate.

Authorization requires explicit Keycloak groups on every login. Dataset and
row access still require separately configured, tested database controls.
"""

import hashlib

from flask import current_app
from superset.security import SupersetSecurityManager


def map_userinfo(data, token_claims, issuer):
    """Reject incomplete/unverified identities and return only required fields."""
    if not isinstance(data, dict) or not isinstance(token_claims, dict):
        raise TypeError("OIDC identity claims are missing")
    subject = data.get("sub")
    if not isinstance(subject, str) or not subject or token_claims.get("sub") != subject:
        raise ValueError("OIDC subject mismatch")
    if data.get("email_verified") is not True or not isinstance(data.get("email"), str) or not data["email"]:
        raise ValueError("OIDC verified email is required")
    groups = data.get("groups")
    if not isinstance(groups, list) or not all(isinstance(group, str) for group in groups):
        raise ValueError("OIDC groups claim is required")
    username = "kc_" + hashlib.sha256((issuer + "\0" + subject).encode()).hexdigest()
    return {"username": username, "email": data["email"],
            "first_name": data.get("given_name") or "", "last_name": data.get("family_name") or "",
            "role_keys": groups}


class KingPacSecurityManager(SupersetSecurityManager):
    def get_oauth_user_info(self, provider, response):
        if provider != "keycloak":
            raise ValueError("Unapproved OIDC provider")
        userinfo = self.oauth_remotes[provider].get(current_app.config["KINGPAC_USERINFO_URL"])
        userinfo.raise_for_status()
        return map_userinfo(userinfo.json(), response.get("userinfo"), current_app.config["KINGPAC_OIDC_ISSUER"])

    def auth_user_oauth(self, userinfo):
        groups = userinfo.get("role_keys", []) if isinstance(userinfo, dict) else []
        approved = current_app.config["AUTH_ROLES_MAPPING"]
        if not isinstance(groups, list) or not any(group in approved for group in groups if isinstance(group, str)):
            return None
        return super().auth_user_oauth(userinfo)
