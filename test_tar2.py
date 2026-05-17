import paramiko
import tarfile

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Clean
stdin, stdout, stderr = client.exec_command('rm -rf /opt/ops-admin/*')
stdout.read()

# List tar contents
cmd = 'python3 -c "import tarfile; t=tarfile.open(\'/opt/ops-admin/ops-deploy.tar.gz\'); [print(m.name) for m in t.getmembers()]"'
stdin, stdout, stderr = client.exec_command(cmd)
print('Tar members:')
for line in stdout.read().decode().split('\n')[:30]:
    print(' ', line)

# Extract using Python
cmd2 = 'python3 -c "import tarfile; t=tarfile.open(\'/opt/ops-admin/ops-deploy.tar.gz\'); t.extractall(\'/opt/ops-admin\'); print(\'done\')"'
stdin, stdout, stderr = client.exec_command(cmd2)
print('Extract result:', stdout.read().decode())

# Check result
stdin, stdout, stderr = client.exec_command('find /opt/ops-admin -maxdepth 2')
print('Result:', stdout.read().decode()[:1000])

client.close()