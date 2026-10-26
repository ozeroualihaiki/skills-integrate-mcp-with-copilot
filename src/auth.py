import hashlib
import hmac
import json
import secrets
from pathlib import Path


ROLES = {"student", "organizer", "admin"}
SCRYPT_N = 2**14


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=8, p=1
    )
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    if len(salt) != 16 or len(expected) != 64:
        return False

    try:
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=8,
            p=1,
            dklen=len(expected),
        )
    except (ValueError, OverflowError):
        return False
    return hmac.compare_digest(actual, expected)


def load_users(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as users_file:
        data = json.load(users_file)

    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise ValueError("User file must contain a 'users' list")

    users: dict[str, dict[str, str]] = {}
    for user in data["users"]:
        if not isinstance(user, dict):
            raise ValueError("Each user must be a JSON object")
        email = user.get("email")
        role = user.get("role")
        password_hash = user.get("password_hash")
        if (
            not isinstance(email, str)
            or not email.strip()
            or not isinstance(role, str)
            or role not in ROLES
            or not isinstance(password_hash, str)
            or not is_valid_password_hash(password_hash)
        ):
            raise ValueError("Each user requires an email, valid role, and scrypt password hash")
        normalized_email = email.strip().lower()
        if normalized_email in users:
            raise ValueError("User emails must be unique")
        users[normalized_email] = {
            "email": normalized_email,
            "role": role,
            "password_hash": password_hash,
        }
    return users


def is_valid_password_hash(encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$")
        return (
            algorithm == "scrypt"
            and len(bytes.fromhex(salt_hex)) == 16
            and len(bytes.fromhex(digest_hex)) == 64
        )
    except (ValueError, TypeError):
        return False
