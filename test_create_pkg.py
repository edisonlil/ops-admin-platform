import sys
sys.path.insert(0, "D:/PyProject/ops-admin-platform/ops-cli")
from ops_cli.commands.deploy import create_deploy_package
from pathlib import Path
import json
import os

project_path = Path("D:/OpsPyProject/ops-project-20260517")
output_path = Path("C:/Users/ediso/test-deploy.tar.gz")

db_config = {"backend": "mysql", "database_url": "mysql://root:passw0rd@192.168.20.121:3306/ops_sale_dev"}

result = create_deploy_package(project_path, output_path, db_config)
print("Result:", result)
print("File size:", os.path.getsize(output_path) if os.path.exists(output_path) else 0)

# Check contents
import tarfile
with tarfile.open(str(output_path), 'r') as tar:
    members = tar.getmembers()
    print("Total members:", len(members))
    
    for m in members[:30]:
        print(f"  {m.name} (dir={m.isdir()}, size={m.size})")