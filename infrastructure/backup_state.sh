#!/bin/bash
# Backup Terraform state files

BACKUP_DIR="$HOME/.terraform_backups/product-catalogue"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup state files
if [ -f "terraform.tfstate" ]; then
    cp terraform.tfstate "$BACKUP_DIR/terraform.tfstate.$TIMESTAMP"
    echo "✓ Backed up terraform.tfstate to $BACKUP_DIR/terraform.tfstate.$TIMESTAMP"
fi

if [ -f "terraform.tfstate.backup" ]; then
    cp terraform.tfstate.backup "$BACKUP_DIR/terraform.tfstate.backup.$TIMESTAMP"
    echo "✓ Backed up terraform.tfstate.backup"
fi

# Keep only last 10 backups
cd "$BACKUP_DIR"
ls -t terraform.tfstate.* | tail -n +11 | xargs -r rm
echo "✓ Cleaned old backups (keeping last 10)"
