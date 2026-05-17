import paramiko
import tarfile

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Clean
stdin, stdout, stderr = client.exec_command('rm -rf /opt/ops-admin/*')
stdout.read()

# Upload test tar
sftp = client.open_sftp()
sftp.put('D:/PyProject/ops-admin-platform/ops-cli/test-deploy.tar.gz', '/opt/ops-admin/ops-deploy.tar.gz')
sftp.close()
print('Uploaded')

# Extract with Python
cmd = 'python3 -c "import tarfile; tarfile.open(\'/opt/ops-admin/ops-deploy.tar.gz\').extractall(\'/opt/ops-admin\'); print(\'extracted\')"'
stdin, stdout, stderr = client.exec_command(cmd)
print('Extract:', stdout.read().decode())

# Check files
stdin, stdout, stderr = client.exec_command('ls -la /opt/ops-admin/')
print('Files:', stdout.read().decode())

# Check Dockerfile
stdin, stdout, stderr = client.exec_command('test -f /opt/ops-admin/Dockerfile && echo "EXISTS" || echo "NOT_FOUND"')
print('Dockerfile:', stdout.read().decode())

client.close()