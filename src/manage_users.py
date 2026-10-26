import argparse
import getpass
import json
import os
from pathlib import Path
import tempfile

from src.auth import ROLES, hash_password, load_users


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a user account for the Mergington activities app."
    )
    parser.add_argument("email")
    parser.add_argument("role", choices=sorted(ROLES))
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not email:
        parser.error("email must not be empty")

    users_path = Path(os.environ.get("USERS_FILE", Path(__file__).parent.parent / "users.json"))
    if users_path.exists():
        users = load_users(users_path)
        if email in users:
            parser.error(f"an account for {email} already exists")
        records = [
            {
                "email": user["email"],
                "role": user["role"],
                "password_hash": user["password_hash"],
            }
            for user in users.values()
        ]
    else:
        records = []

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        parser.error("password must be at least 12 characters")
    if password != confirmation:
        parser.error("passwords do not match")

    records.append(
        {"email": email, "role": args.role, "password_hash": hash_password(password)}
    )
    users_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        dir=users_path.parent, prefix=f".{users_path.name}."
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as users_file:
            json.dump({"users": records}, users_file, indent=2)
            users_file.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, users_path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    print(f"Created {args.role} account for {email} in {users_path}")


if __name__ == "__main__":
    main()
