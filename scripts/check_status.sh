#!/bin/bash
# Script to check the status of the Inventory API on EC2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"
EC2_USER="ec2-user"

echo "=========================================="
echo "CHECKING INVENTORY API EC2 STATUS"
echo "=========================================="

# Get EC2 instance details from Terraform output
EC2_PUBLIC_IP=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw inventory_api_public_ip 2>/dev/null || echo "")
EC2_PUBLIC_DNS=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw inventory_api_public_dns 2>/dev/null || echo "")
KEY_PAIR=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw ec2_key_pair 2>/dev/null || echo "vockey")

if [ -z "$EC2_PUBLIC_IP" ] && [ -z "$EC2_PUBLIC_DNS" ]; then
    echo "Error: Could not retrieve EC2 instance details from Terraform output."
    echo "Make sure Terraform has been applied."
    exit 1
fi

EC2_HOST="${EC2_PUBLIC_DNS:-$EC2_PUBLIC_IP}"
echo "EC2 Instance (Inventory API): $EC2_HOST"
echo ""

# Find SSH key
SSH_KEY=""
if [ -f "$HOME/.ssh/${KEY_PAIR}.pem" ]; then
    SSH_KEY="$HOME/.ssh/${KEY_PAIR}.pem"
elif [ -f "$HOME/.ssh/${KEY_PAIR}" ]; then
    SSH_KEY="$HOME/.ssh/${KEY_PAIR}"
elif [ -f "$INFRASTRUCTURE_DIR/${KEY_PAIR}.pem" ]; then
    SSH_KEY="$INFRASTRUCTURE_DIR/${KEY_PAIR}.pem"
else
    echo "Error: Could not find SSH key for ${KEY_PAIR}"
    exit 1
fi

echo "Using SSH key: $SSH_KEY"
echo ""

# Check service status
echo "Checking Inventory API service status..."
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_CHECK'
    echo "=========================================="
    echo "INVENTORY API SERVICE STATUS"
    echo "=========================================="
    sudo systemctl status inventory_api --no-pager || echo "Service not found or not running"
    echo ""
    
    echo "=========================================="
    echo "INVENTORY API LOGS (last 20 lines)"
    echo "=========================================="
    sudo journalctl -u inventory_api -n 20 --no-pager || echo "No logs found"
    echo ""
    
    echo "=========================================="
    echo "LISTENING PORTS"
    echo "=========================================="
    sudo netstat -tlnp 2>/dev/null | grep -E ':(9000|8000)' || ss -tlnp 2>/dev/null | grep -E ':(9000|8000)' || echo "No services listening on ports 8000 or 9000"
    echo ""
    
    echo "=========================================="
    echo "DEPLOYMENT DIRECTORY CHECK"
    echo "=========================================="
    ls -la /opt/inventory_api/ 2>/dev/null || echo "Deployment directory not found"
    echo ""
    
    echo "=========================================="
    echo "TESTING LOCAL CONNECTION"
    echo "=========================================="
    curl -s http://localhost:9000/health | head -c 200 || echo "Failed to connect to Inventory API on localhost:9000"
    echo ""
REMOTE_CHECK

echo ""
echo "=========================================="
echo "TERRAFORM OUTPUTS"
echo "=========================================="
terraform -chdir="$INFRASTRUCTURE_DIR" output -json 2>/dev/null | grep -q "inventory_api" && echo "✓ Terraform outputs available"
echo ""
echo "Inventory API URL (internal): $(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw inventory_api_url 2>/dev/null || echo "N/A")"
echo "Application URL (if publicly accessible): http://$EC2_HOST:9000"
echo ""
