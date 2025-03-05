#!/usr/bin/env python3
# flake8: noqa
import getpass
import os
import sys
import warnings

from sqlalchemy.orm import Session

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_password_hash
from app.crud.users import get_user_by_username
from app.database import SessionLocal


def reset_password(username: str, new_password: str) -> bool:
    """
    Reset the password for a user.

    Args:
        username: The username of the user whose password to reset
        new_password: The new password to set

    Returns:
        bool: True if successful, False otherwise
    """
    db: Session = SessionLocal()
    try:
        user = get_user_by_username(db, username)
        if not user:
            print(f"Error: User '{username}' not found")
            return False

        user.hashed_password = get_password_hash(new_password)
        db.commit()

        print(f"Password for user '{username}' has been reset successfully")
        return True
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False
    finally:
        db.close()


def main():
    print("=== Password Reset Tool ===")

    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        sys.exit(1)

    password = getpass.getpass("Enter new password: ")
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)

    confirm_password = getpass.getpass("Confirm new password: ")
    if password != confirm_password:
        print("Error: Passwords do not match")
        sys.exit(1)

    success = reset_password(username, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
