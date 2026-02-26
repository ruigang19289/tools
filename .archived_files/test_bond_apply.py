#!/usr/bin/env python3
"""Test bond configuration with IP range splitting"""
import requests
import json

# Test configuration
servers = ["192.168.23.5", "192.168.23.6"]
username = "root"
password = "password"

bond_config = {
    "name": "bond0",
    "mode": "1",
    "slaves": ["ens34", "ens35"],
    "ip": "192.168.32.7-192.168.32.8/24",
    "gateway": "192.168.32.254",
    "dns": ""
}

print("Testing bond configuration with IP range splitting...")
print(f"IP Range: {bond_config['ip']}")
print(f"Expected: Server 1 gets 192.168.32.7, Server 2 gets 192.168.32.8")
print()

# Apply configuration to each server
for server_index, server in enumerate(servers):
    print(f"\n{'='*60}")
    print(f"Applying to server {server_index + 1}: {server}")
    print(f"{'='*60}")

    response = requests.post(
        "http://localhost:6000/api/v1/network/bond/apply-bond",
        json={
            "servers": [server],
            "server_index": server_index,
            "username": username,
            "password": password,
            "bond_configs": [bond_config]
        }
    )

    result = response.json()
    print(f"Status: {result.get('status')}")

    if result.get('results'):
        server_result = result['results'][0]
        print(f"Server status: {server_result.get('status')}")

        if server_result.get('bonds'):
            bond_result = server_result['bonds'][0]
            print(f"Bond success: {bond_result.get('success')}")
            print(f"Message: {bond_result.get('message')}")

            if bond_result.get('logs'):
                print("\nLogs:")
                for log in bond_result['logs']:
                    print(f"  [{log.get('level')}] {log.get('message')}")

print("\n" + "="*60)
print("Verification")
print("="*60)

# Verify the configuration
import paramiko

for server in servers:
    print(f"\n--- Server: {server} ---")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username, password=password)

    # Check bond IP
    stdin, stdout, stderr = client.exec_command("grep IPADDR /etc/sysconfig/network-scripts/ifcfg-bond0")
    print(f"Bond IP: {stdout.read().decode('utf-8').strip()}")

    # Check slave files
    stdin, stdout, stderr = client.exec_command("ls -1 /etc/sysconfig/network-scripts/ifcfg-ens3* 2>/dev/null | grep -v '.bak'")
    slave_files = stdout.read().decode('utf-8').strip().split('\n')
    print(f"Slave config files: {', '.join([f.split('/')[-1] for f in slave_files if f])}")

    # Check if slaves have SLAVE=yes
    for slave_file in slave_files:
        if slave_file and 'ens3' in slave_file:
            stdin, stdout, stderr = client.exec_command(f"grep -E 'SLAVE=|MASTER=' {slave_file}")
            slave_config = stdout.read().decode('utf-8').strip()
            if slave_config:
                print(f"  {slave_file.split('/')[-1]}: {slave_config.replace(chr(10), ', ')}")

    # Check bond slaves
    stdin, stdout, stderr = client.exec_command("cat /sys/class/net/bond0/bonding/slaves 2>/dev/null || echo 'No slaves'")
    print(f"Active bond slaves: {stdout.read().decode('utf-8').strip()}")

    client.close()

print("\nTest complete!")
