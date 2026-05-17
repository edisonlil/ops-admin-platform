import paramiko
import tarfile
import io
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Clean
stdin, stdout, stderr = client.exec_command('rm -rf /opt/ops-admin/*')
stdout.read()

# Create a fresh tar with real content
tar_buf = io.BytesIO()
with tarfile.open(fileobj=tar_buf, mode='w') as tar:
    # Add some test files
    for name in ['api/test.txt', 'packages/test.txt', 'dist/index.html']:
        info = tarfile.TarInfo(name=name)
        content = f'test content for {name}'.encode()
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))

tar_buf.seek(0)
print('Created tar, size:', len(tar_buf.getvalue()))

# Upload
sftp = client.open_sftp()
sftp.putfo(tar_buf, '/opt/ops-admin/test.tar.gz')
sftp.close()

# List server files
stdin, stdout, stderr = client.exec_command('ls -la /opt/ops-admin/')
print('Server files:', stdout.read().decode())

# Read tar and extract
stdin, stdout, stderr = client.exec_command('python3 -c "import tarfile; t=tarfile.open(\'/opt/ops-admin/test.tar.gz\'); [print(m.name) for m in t.getmembers()]"')
print('Members:', stdout.read().decode())

# Extract
stdin, stdout, stderr = client.exec_command('python3 -c "import tarfile; tarfile.open(\'/opt/ops-admin/test.tar.gz\').extractall(\'/opt/ops-admin\')"')
print('Extract:', stdout.read().decode())

# Check
stdin, stdout, stderr = client.exec_command('find /opt/ops-admin -type f')
print('Files:', stdout.read().decode())

client.close()