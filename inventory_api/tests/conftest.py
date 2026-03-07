import sys
import os

# Add the inventory_api root to sys.path so test files can import app modules
# (main, inventory_dao, sales_dao, inventory, config, etc.)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
