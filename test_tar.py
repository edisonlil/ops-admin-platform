import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check with python
cmd = 'python3 -c "import tarfile; t=tarfile.open(\'/opt/ops-admin/test.tar.gz\'); print([m.name for m in t.getmembers()])"'
stdin, stdout, stderr = client.exec_command(cmd)
print('Python tar:', stdout.read().decode())
print('Error:', stderr.read().decode())

# Try extract
cmd2 = 'python3 -c "import tarfile; t=tarfile.open(\'/opt/ops-admin/test.tar.gz\'); t.extractall(\'/opt/ops-admin\'); print(\'extracted\')"'
stdin, stdout, stderr = client.exec_command(cmd2)
print('Extract:', stdout.read().decode())
print('Error:', stderr.read().decode())

# Check result
stdin, stdout, stderr = client.exec_command('ls -la /opt/ops-admin/')
print('Result:', stdout.read().decode())

client.close()