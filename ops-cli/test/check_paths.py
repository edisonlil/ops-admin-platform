import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check docker-compose.yml
stdin, stdout, stderr = client.exec_command('cat /opt/ops-admin/docker-compose.yml')
print('docker-compose.yml:')
print(stdout.read().decode())

# Check what's in container
stdin, stdout, stderr = client.exec_command('docker exec ops-admin-backend ls -la /app/')
print('\nContainer /app/:')
print(stdout.read().decode())

# Check dist in container
stdin, stdout, stderr = client.exec_command('docker exec ops-admin-backend ls -la /app/dist/ 2>&1')
print('\nContainer /app/dist/:')
print(stdout.read().decode())

# Check dist in ops-admin
stdin, stdout, stderr = client.exec_command('ls -la /opt/ops-admin/dist/')
print('\nServer /opt/ops-admin/dist/:')
print(stdout.read().decode())

client.close()