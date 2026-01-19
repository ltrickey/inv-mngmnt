#!/bin/bash
# Script to check the status of the deployed application on EC2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
EC2_USER="ec2-user"

echo "=========================================="
echo "CHECKING EC2 DEPLOYMENT STATUS"
echo "=========================================="

# Get EC2 instance details from Terraform output
cd "$INFRASTRUCTURE_DIR"
EC2_PUBLIC_IP=$(terraform output -raw ec2_instance_public_ip 2>/dev/null || echo "")
EC2_PUBLIC_DNS=$(terraform output -raw ec2_instance_public_dns 2>/dev/null || echo "")
KEY_PAIR=$(terraform output -raw ec2_key_pair 2>/dev/null || echo "vockey")

if [ -z "$EC2_PUBLIC_IP" ] && [ -z "$EC2_PUBLIC_DNS" ]; then
    echo "Error: Could not retrieve EC2 instance details from Terraform output."
    echo "Make sure Terraform has been applied."
    exit 1
fi

EC2_HOST="${EC2_PUBLIC_DNS:-$EC2_PUBLIC_IP}"
echo "EC2 Instance: $EC2_HOST"
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
echo "Checking Flask service status..."
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_CHECK'
    echo "=========================================="
    echo "FLASK SERVICE STATUS"
    echo "=========================================="
    sudo systemctl status product_catalogue_flask --no-pager || echo "Service not found or not running"
    echo ""
    
    echo "=========================================="
    echo "FLASK SERVICE LOGS (last 20 lines)"
    echo "=========================================="
    sudo journalctl -u product_catalogue_flask -n 20 --no-pager || echo "No logs found"
    echo ""
    
    echo "=========================================="
    echo "LISTENING PORTS"
    echo "=========================================="
    sudo netstat -tlnp | grep -E ':(8000|3000)' || echo "No services listening on ports 8000 or 3000"
    echo ""
    
    echo "=========================================="
    echo "DEPLOYMENT DIRECTORY CHECK"
    echo "=========================================="
    ls -la /opt/product_catalogue/ 2>/dev/null || echo "Deployment directory not found"
    echo ""
    
    echo "=========================================="
    echo "REACT BUILD CHECK"
    echo "=========================================="
    ls -la /opt/product_catalogue/site-dist/ 2>/dev/null || echo "React build directory not found"
    echo ""
    
    echo "=========================================="
    echo "FLASK APP CHECK"
    echo "=========================================="
    ls -la /opt/product_catalogue/server/ 2>/dev/null || echo "Server directory not found"
    echo ""
    
    echo "=========================================="
    echo "TESTING LOCAL CONNECTION"
    echo "=========================================="
    curl -s http://localhost:8000/products | head -c 200 || echo "Failed to connect to Flask on localhost:8000"
    echo ""
REMOTE_CHECK

echo ""
echo "=========================================="
echo "SECURITY GROUP CHECK"
echo "=========================================="
echo "Checking if security group allows port 8000..."
cd "$INFRASTRUCTURE_DIR"
terraform output -json 2>/dev/null | grep -q "ec2_instance" && echo "✓ Terraform outputs available"
echo ""
echo "To check security group rules, run:"
echo "  aws ec2 describe-security-groups --group-ids \$(terraform output -raw security_group_id)"
echo ""
echo "Application URL: http://$EC2_HOST:8000"
