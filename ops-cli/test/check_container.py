import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check if fastapi is in the image
stdin, stdout, stderr = client.exec_command('docker run --rm ops-admin:latest python3 -c "import fastapi; print(fastapi.__version__)"')
print('FastAPI version in container:')
print(stdout.read().decode())

# Check CMD in Dockerfile
stdin, stdout, stderr = client.exec_command('docker inspect ops-admin:latest --format "{{.Config.Cmd}}"')
print('\nContainer CMD:')
print(stdout.read().decode())

# Check if pip installed packages
stdin, stdout, stderr = client.exec_command('docker run --rm ops-admin:latest pip list | grep -i fast')
print('\nInstalled packages:')
print(stdout.read().decode())

client.close()