#!/usr/bin/env python3
"""
Helper script to create a test midwife account and return a JWT token.

Usage:
    python scripts/create_test_account.py --email user@example.com --password mypass
    python scripts/create_test_account.py  # prompts for email and password
"""

import argparse
import sys
import requests
import json


def main():
    parser = argparse.ArgumentParser(
        description="Create a test midwife account and return a token."
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Email address for the test account",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="Password for the test account",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    # Prompt if not provided via args
    email = args.email
    if not email:
        email = input("Enter email: ").strip()
    
    password = args.password
    if not password:
        import getpass
        password = getpass.getpass("Enter password: ")

    if not email or not password:
        print("Error: email and password are required.", file=sys.stderr)
        sys.exit(1)

    endpoint = f"{args.url}/api/v1/auth/test-account"
    payload = {"email": email, "password": password}

    try:
        response = requests.post(endpoint, json=payload, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to reach {endpoint}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response: {e}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    if response.status_code not in (200, 201):
        print(f"Error: {response.status_code} - {data.get('detail', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)

    email_result = data.get("email")
    token = data.get("token")

    print(f"\n✓ Test account created successfully!")
    print(f"  Email:  {email_result}")
    print(f"  Token:  {token}")
    print(f"\nUse this token in the Authorization header: Bearer {token}\n")


if __name__ == "__main__":
    main()
