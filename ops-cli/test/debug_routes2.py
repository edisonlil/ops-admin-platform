import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check all routes
cmd = 'docker exec ops-admin-backend python3 -c "from api.main import app; routes = [r.path for r in app.routes]; print(routes)"'
stdin, stdout, stderr = client.exec_command(cmd)
print('All routes:')
routes_str = stdout.read().decode()
print(routes_str)

# Check if identity_access is imported
cmd2 = 'docker exec ops-admin-backend python3 -c "import sys; sys.path.insert(0, \'/app\'); from api import routes; print(dir(routes))"'
stdin, stdout, stderr = client.exec_command(cmd2)
print('\nRoutes module:')
print(stdout.read().decode())

# Check module_registry
cmd3 = 'docker exec ops-admin-backend python3 -c "import sys; sys.path.insert(0, \'/app\'); from api.module_registry import MODULES; print(MODULES)"'
stdin, stdout, stderr = client.exec_command(cmd3)
print('\nModule registry:')
print(stdout.read().decode())

client.close()