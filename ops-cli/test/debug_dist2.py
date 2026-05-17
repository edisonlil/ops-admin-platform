import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Debug admin_dist_path with print
cmd = 'docker exec ops-admin-backend python3 << EOF\nimport sys\nsys.path.insert(0, \"/app\")\nfrom system.infrastructure.config import repo_root, admin_dist_path\nprint(\"repo_root:\", repo_root())\ndp = admin_dist_path()\nprint(\"dist_path:\", dp)\nprint(\"exists:\", dp.exists())\nindex = dp / \"index.html\"\nprint(\"index.html exists:\", index.exists() if dp.exists() else \"parent not exists\")\nEOF'
stdin, stdout, stderr = client.exec_command(cmd)
print('Debug dist path:')
print(stdout.read().decode())
print('Errors:', stderr.read().decode()[:500])

client.close()