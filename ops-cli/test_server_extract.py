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

# Check tar contents with Python
stdin, stdout, stderr = client.exec_command('python3 -c "import tarfile; t=tarfile.open(\'/opt/ops-admin/ops-deploy.tar.gz\'); print([m.name for m in t.getmembers()[:20]])"')
print('Python check:', stdout.read().decode())

# Extract
stdin, stdout, stderr = client.exec_command('python3 -c "import tarfile; tarfile.open(\'/opt/ops-admin/ops-deploy.tar.gz\').extractall(\'/opt/ops-admin\'); print(\'extracted\')"')
print('Extract:', stdout.read().decode())

# Check result
stdin, stdout, stderr = client.exec_command('find /opt/ops-admin -maxdepth 2 -type d')
print('Dirs:', stdout.read().decode())

client.close()