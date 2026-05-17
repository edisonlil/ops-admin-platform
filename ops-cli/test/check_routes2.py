import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check env vars
stdin, stdout, stderr = client.exec_command('docker exec ops-admin-backend env')
print('Env vars:')
env_lines = stdout.read().decode().split('\n')
for line in env_lines:
    if 'DIST' in line or 'ADMIN' in line or 'FG_AGENT' in line:
        print(line)

# Check mount_admin function
cmd = 'docker exec ops-admin-backend python3 -c "import sys; sys.path.insert(0, \'/app\'); from api.main import mount_admin, create_app; app = create_app(); print(\'app routes:\', [r.path for r in app.routes][:10])"'
stdin, stdout, stderr = client.exec_command(cmd)
print('\nApp routes:')
print(stdout.read().decode())

client.close()