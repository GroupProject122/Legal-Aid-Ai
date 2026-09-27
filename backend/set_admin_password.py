"""Set (or reset) the admin account's password.

    python set_admin_password.py

Creates the admin account first if it does not exist yet (and assigns any cases/documents saved
before accounts were introduced to it, exactly as server startup does). The password is typed at
a hidden prompt, never passed on the command line, so it does not end up in shell history. Every
existing admin session is signed out.
"""
from __future__ import annotations

import getpass
import sys

import auth


def main() -> int:
    auth.init_db()
    admin = auth.ensure_admin()
    claimed = auth.claim_unowned_data()
    if claimed["cases"] or claimed["documents"]:
        print(f"Assigned {claimed['cases']} case(s) and {claimed['documents']} document(s) to the admin account.")
    identifier = admin["email"] or admin["phone"]
    print(f"Admin account: {identifier}")
    password = getpass.getpass("New password: ")
    if password != getpass.getpass("Repeat new password: "):
        print("Passwords do not match; nothing changed.")
        return 1
    try:
        auth.set_password(admin["id"], password)
    except auth.AuthError as exc:
        print(f"{exc} Nothing changed.")
        return 1
    print("Admin password updated. Sign in with the account above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
