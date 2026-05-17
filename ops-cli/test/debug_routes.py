import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check router using different method
cmd = 'docker exec ops-admin-backend python3 -c "from api.main import app; routes = []; [routes.extend([r.path, getattr(r, \'methods\', None)]) for r in app.routes if hasattr(r, \'path\')]; print([r for r in app.routes][:10])"'
stdin, stdout, stderr = client.exec_command(cmd)
print('First 10 routes:')
print(stdout.read().decode())
print('Errors:', stderr.read().decode()[:500])

# Check if identity_access module is loaded
cmd2 = 'docker exec ops-admin-backend python3 -c "import sys; sys.path.insert(0, \'/app\'); from api.module_registry import registry; print(registry.modules)"'
stdin, stdout, stderr = client.exec_command(cmd2)
print('\nModule registry:')
print(stdout.read().decode())

client.close()