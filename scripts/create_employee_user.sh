#!/bin/bash
# Create a Cognito user for the employee-facing website.
#
# Usage:
#   ./scripts/create_employee_user.sh --email alice@store.com
#   ./scripts/create_employee_user.sh --email alice@store.com --username alice
#   ./scripts/create_employee_user.sh --email bob@store.com --user-pool-id us-east-1_XXXXX
#
# If --user-pool-id is omitted, the script reads cognito_user_pool_id from
# infrastructure/ Terraform outputs (requires terraform applied).
# The user receives a temporary password and must change it on first login.
# Requires: AWS CLI, credentials with cognito-idp:AdminCreateUser.

set -e

USER_POOL_ID="${COGNITO_USER_POOL_ID:-}"
REGION="${AWS_REGION:-us-east-1}"
EMAIL=""
USERNAME=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --email)
      EMAIL="$2"
      shift 2
      ;;
    --username)
      USERNAME="$2"
      shift 2
      ;;
    --user-pool-id)
      USER_POOL_ID="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$EMAIL" ]]; then
  echo "Error: --email is required" >&2
  exit 1
fi

if [[ -z "$USER_POOL_ID" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  INFRA_DIR="$(cd "$SCRIPT_DIR/../infrastructure" && pwd)"
  if [[ -d "$INFRA_DIR" ]]; then
    USER_POOL_ID="$(terraform -chdir="$INFRA_DIR" output -raw cognito_user_pool_id 2>/dev/null)" || true
    if [[ -n "$USER_POOL_ID" ]]; then
      # Use Terraform's region when we're reading from Terraform (unless already set)
      if [[ -z "${AWS_REGION:-}" ]]; then
        REGION="$(terraform -chdir="$INFRA_DIR" output -raw aws_region 2>/dev/null)" || true
        REGION="${REGION:-us-east-1}"
      fi
    fi
  fi
  if [[ -z "$USER_POOL_ID" ]]; then
    echo "Error: --user-pool-id is required (or set COGNITO_USER_POOL_ID, or run from a repo with Terraform applied in infrastructure/)" >&2
    exit 1
  fi
fi

USERNAME="${USERNAME:-$EMAIL}"

# Generate a 12-char temporary password: at least one upper, lower, digit, special
gen_char() {
  local set="$1"
  echo -n "${set:$((RANDOM % ${#set})):1}"
}
SPECIAL='!@#$%'
LETTERS_LOWER='abcdefghijklmnopqrstuvwxyz'
LETTERS_UPPER='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
DIGITS='0123456789'
ALPHANUM="$LETTERS_LOWER$LETTERS_UPPER$DIGITS$SPECIAL"
TEMP_PW="$(gen_char "$LETTERS_UPPER")$(gen_char "$LETTERS_LOWER")$(gen_char "$DIGITS")$(gen_char "$SPECIAL")"
for _ in {1..8}; do
  TEMP_PW+="$(gen_char "$ALPHANUM")"
done
# Shuffle (portable: perl on macOS, shuf on Linux)
if command -v shuf &>/dev/null; then
  TEMP_PW="$(echo -n "$TEMP_PW" | fold -w1 | shuf | tr -d '\n')"
else
  TEMP_PW="$(perl -e "print sort { rand() <=> rand() } split //, \$ARGV[0]" "$TEMP_PW")"
fi

OUTPUT="$(aws cognito-idp admin-create-user \
  --region "$REGION" \
  --user-pool-id "$USER_POOL_ID" \
  --username "$USERNAME" \
  --user-attributes "Name=email,Value=$EMAIL" "Name=email_verified,Value=true" \
  --temporary-password "$TEMP_PW" \
  --message-action SUPPRESS \
  2>&1)" || EXIT_CODE=$?

if [[ ${EXIT_CODE:-0} -ne 0 ]]; then
  if echo "$OUTPUT" | grep -q "UsernameExistsException"; then
    echo "Error: User '$USERNAME' already exists in the pool." >&2
  else
    echo "$OUTPUT" >&2
  fi
  exit 1
fi

echo "User created successfully!"
echo "  Username:           $USERNAME"
echo "  Email:              $EMAIL"
echo "  Temporary password: $TEMP_PW"
echo "  Status:             FORCE_CHANGE_PASSWORD"
echo ""
echo "The user must change their password on first login."
