import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Check router
cmd = 'cd /opt/ops-admin && python3 -c "from api.main import app; routes = [str(r.path) for r in app.routes]; print(routes)"'
stdin, stdout, stderr = client.exec_command(cmd)
print('Routes:')
print(stdout.read().decode()[:2000])
print('Errors:', stderr.read().decode()[:500])

client.close()