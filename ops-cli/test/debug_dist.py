import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Debug admin_dist_path
cmd = 'docker exec ops-admin-backend python3 -c "from api.config import admin_dist_path; dp = admin_dist_path(); print(f\"dist_path: {dp}\"); print(f\"exists: {dp.exists()}\"); print(f\"index.html: {(dp / \\"index.html\\").exists()}\")"'
stdin, stdout, stderr = client.exec_command(cmd)
print('Admin dist path:')
print(stdout.read().decode())

# Check system config
cmd2 = 'docker exec ops-admin-backend python3 -c "from system.infrastructure.config import admin_dist_path; dp = admin_dist_path(); print(f\"dist_path: {dp}\"); print(f\"exists: {dp.exists()}\")"'
stdin, stdout, stderr = client.exec_command(cmd2)
print('\nSystem config admin_dist_path:')
print(stdout.read().decode())

client.close()