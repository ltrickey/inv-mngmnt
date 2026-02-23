#!/usr/bin/env python3
"""Create a Cognito user for the employee-facing website.

Usage:
    python create_user.py --email alice@store.com
    python create_user.py --email alice@store.com --username alice
    python create_user.py --email bob@store.com --user-pool-id us-east-1_XXXXX

The user will receive a temporary password and must change it on first login.
"""

import argparse
import os
import secrets
import string
import sys

import boto3


def generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    # Guarantee at least one of each required character class
    pw = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%"),
    ]
    pw += [secrets.choice(alphabet) for _ in range(length - len(pw))]
    # Shuffle so the guaranteed chars aren't always first
    result = list(pw)
    secrets.SystemRandom().shuffle(result)
    return "".join(result)


def main():
    parser = argparse.ArgumentParser(description="Create a Cognito employee user")
    parser.add_argument("--email", required=True, help="Employee email address")
    parser.add_argument("--username", default=None, help="Username (defaults to email)")
    parser.add_argument(
        "--user-pool-id",
        default=os.environ.get("COGNITO_USER_POOL_ID", ""),
        help="Cognito User Pool ID (or set COGNITO_USER_POOL_ID env var)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region",
    )
    args = parser.parse_args()

    if not args.user_pool_id:
        print("Error: --user-pool-id is required (or set COGNITO_USER_POOL_ID)")
        sys.exit(1)

    username = args.username or args.email
    temp_password = generate_temp_password()

    client = boto3.client("cognito-idp", region_name=args.region)

    try:
        resp = client.admin_create_user(
            UserPoolId=args.user_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email", "Value": args.email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",  # Don't send the welcome email; print creds instead
        )
        user = resp["User"]
        print(f"User created successfully!")
        print(f"  Username:           {user['Username']}")
        print(f"  Email:              {args.email}")
        print(f"  Temporary password: {temp_password}")
        print(f"  Status:             {user['UserStatus']}")
        print()
        print("The user must change their password on first login.")
    except client.exceptions.UsernameExistsException:
        print(f"Error: User '{username}' already exists in the pool.")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
