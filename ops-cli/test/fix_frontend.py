import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.20.121', 22, 'root', 'passw0rd', timeout=30)

# Update docker-compose.yml to mount dist
compose = '''version: '3.8'

services:
  backend:
    image: ops-admin:latest
    container_name: ops-admin-backend
    ports:
      - "8000:8000"
    environment:
      - OPS_ADMIN_APPLICATION_CONFIG=/app/config/application.json
      - FG_AGENT_CORS_ORIGINS=http://localhost:80,http://127.0.0.1:80,http://192.168.20.121:8000
      - FG_AGENT_ADMIN_DIST_PATH=/app/dist
    volumes:
      - ./config:/app/config:ro
      - ./dist:/app/dist:ro
      - ./data:/app/data
    restart: unless-stopped

networks:
  default:
    name: ops-network
'''

sftp = client.open_sftp()
with sftp.open('/opt/ops-admin/docker-compose.yml', 'w') as f:
    f.write(compose)
sftp.close()
print('Updated docker-compose.yml')

# Restart container
stdin, stdout, stderr = client.exec_command('cd /opt/ops-admin && docker-compose down && docker-compose up -d')
print(stdout.read().decode())

# Wait for container to start
import time
time.sleep(5)

# Test frontend
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:8000/ | head -10')
print('\nFrontend test:')
print(stdout.read().decode())

client.close()
