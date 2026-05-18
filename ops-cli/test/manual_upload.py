"""Manual upload script for testing deployment."""
import os
import subprocess
import paramiko
from pathlib import Path

# Connect to server
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)
sftp = client.open_sftp()

remote_path = '/opt/ops-admin'
project_path = Path('D:/OpsPyProject/ops-project-20260517')
scaffold_path = Path('D:/PyProject/ops-admin-platform')

# Clean and create directory
print('Cleaning remote directory...')
stdin, stdout, stderr = client.exec_command(f'rm -rf {remote_path} && mkdir -p {remote_path}/config')
stdout.channel.recv_exit_status()

# Upload deploy.sh
deploy_sh = '''#!/bin/bash
set -e
DEPLOY_DIR="/opt/ops-admin"
REQUIRED_DIRS=("api" "packages" "dist")
echo "Starting deployment..."
cd "$DEPLOY_DIR"
echo "Working directory: $(pwd)"
for d in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$d" ]; then
        echo "  Missing: $d"
    else
        echo "  Found: $d"
    fi
done
if ! docker image inspect ops-admin:latest > /dev/null 2>&1; then
    echo "Building image..."
    docker build -t ops-admin:latest .
fi
echo "Starting container..."
docker-compose up -d
sleep 3
docker ps | grep ops-admin || echo "Container check done"
'''

with sftp.open(f'{remote_path}/deploy.sh', 'w') as f:
    f.write(deploy_sh)
print('Uploaded deploy.sh')

# Upload docker-compose.yml
compose = scaffold_path / 'docker-compose.yml'
if compose.exists():
    with sftp.open(f'{remote_path}/docker-compose.yml', 'w') as f:
        f.write(compose.read_text())
    print('Uploaded docker-compose.yml')

# Upload application config
app_config = '{"database": {"backend": "mysql", "database_url": "mysql://root:passw0rd@192.168.20.121:3306/ops_sale_dev"}}'
with sftp.open(f'{remote_path}/config/application.json', 'w') as f:
    f.write(app_config)
print('Uploaded application.json')

# Upload api directory
print('Uploading api...')
tar_path = 'C:/Users/ediso/api-upload.tar.gz'
subprocess.run(['tar', '-czf', tar_path, '-C', str(project_path), 'api'], capture_output=True)

with open(tar_path, 'rb') as f:
    sftp.putfo(f, f'{remote_path}/api-upload.tar.gz')

stdin, stdout, stderr = client.exec_command(f'cd {remote_path} && tar -xzf api-upload.tar.gz && rm api-upload.tar.gz')
stdout.channel.recv_exit_status()
print('Uploaded api')

# Upload packages/python
print('Uploading packages...')
tar_path = 'C:/Users/ediso/packages-upload.tar.gz'
subprocess.run(['tar', '-czf', tar_path, '-C', str(project_path), 'packages'], capture_output=True)

with open(tar_path, 'rb') as f:
    sftp.putfo(f, f'{remote_path}/packages-upload.tar.gz')

stdin, stdout, stderr = client.exec_command(f'cd {remote_path} && tar -xzf packages-upload.tar.gz && rm packages-upload.tar.gz')
stdout.channel.recv_exit_status()
print('Uploaded packages')

# Upload dist
print('Uploading dist...')
tar_path = 'C:/Users/ediso/dist-upload.tar.gz'
subprocess.run(['tar', '-czf', tar_path, '-C', str(project_path / 'web/admin'), 'dist'], capture_output=True)

with open(tar_path, 'rb') as f:
    sftp.putfo(f, f'{remote_path}/dist-upload.tar.gz')

stdin, stdout, stderr = client.exec_command(f'cd {remote_path} && tar -xzf dist-upload.tar.gz && rm dist-upload.tar.gz')
stdout.channel.recv_exit_status()
print('Uploaded dist')

# Upload Dockerfile
dockerfile = scaffold_path / 'Dockerfile'
with sftp.open(f'{remote_path}/Dockerfile', 'w') as f:
    f.write(dockerfile.read_text())
print('Uploaded Dockerfile')

# Upload requirements.txt
requirements = project_path / 'requirements.txt'
if requirements.exists():
    with sftp.open(f'{remote_path}/requirements.txt', 'w') as f:
        f.write(requirements.read_text())
    print('Uploaded requirements.txt')

sftp.close()

# Run deploy script
print('\nRunning deploy script...')
stdin, stdout, stderr = client.exec_command(f'cd {remote_path} && chmod +x deploy.sh && ./deploy.sh')

# Read output
while True:
    if stdout.channel.recv_ready():
        data = stdout.read(4096).decode()
        if data:
            print(data, end='')
    if stdout.channel.exit_status_ready():
        break

exit_status = stdout.channel.recv_exit_status()
print(f'\nDeploy exit status: {exit_status}')

# Check result
stdin, stdout, stderr = client.exec_command('docker ps | grep ops-admin')
print('Container status:', stdout.read().decode())

client.close()
print('\nDone!')
