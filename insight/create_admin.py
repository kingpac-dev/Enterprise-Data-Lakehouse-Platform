"""Create the initial UAT administrator once; never rotate an existing account."""

import os

from superset.app import create_app


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    username = required("INSIGHT_ADMIN_USERNAME")
    email = required("INSIGHT_ADMIN_EMAIL")
    app = create_app()
    with app.app_context():
        from superset import security_manager

        if security_manager.find_user(username=username):
            print("Initial admin already exists; account was not modified.")
            return
        password = required("INSIGHT_ADMIN_PASSWORD")
        if len(password) < 16:
            raise RuntimeError("Initial admin password must be at least 16 characters")
        role = security_manager.find_role("Admin")
        if role is None:
            raise RuntimeError("Admin role is missing; run superset init first")
        user = security_manager.add_user(username, "Insight", "Administrator", email, role, password)
        if not user:
            raise RuntimeError("Initial admin creation failed")
        print("Initial UAT admin created.")


if __name__ == "__main__":
    main()
