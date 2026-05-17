import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Test static file route
cmd = 'docker exec ops-admin-backend python3 -c "from api.main import app; print([r.path for r in app.routes if \"static\" in str(r)])"'
stdin, stdout, stderr = client.exec_command(cmd)
print('Static routes:')
print(stdout.read().decode())

# Check if mount_admin ran correctly
cmd2 = 'docker exec ops-admin-backend python3 -c "from api.main import app; print([(r.path, getattr(r, \"directory\", None)) for r in app.routes if hasattr(r, \"directory\")])"'
stdin, stdout, stderr = client.exec_command(cmd2)
print('\nMounted directories:')
print(stdout.read().decode())

# Try to access index.html directly
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/index.html')
print('\nIndex.html direct:')
print(stdout.read().decode()[:200])

client.close()