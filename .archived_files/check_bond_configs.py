#!/usr/bin/env python3
"""Check bond configuration files on remote servers"""
import paramiko
import sys

def check_server(host, username, password):
    print(f"\n{'='*60}")
    print(f"Checking server: {host}")
    print(f"{'='*60}")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=10)

        # List all network config files
        print("\n1. All network config files:")
        stdin, stdout, stderr = client.exec_command("ls -la /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null")
        output = stdout.read().decode('utf-8')
        if output:
            print(output)
        else:
            print("No config files found")

        # Check for bond interfaces
        print("\n2. Bond interfaces from bonding_masters:")
        stdin, stdout, stderr = client.exec_command("cat /sys/class/net/bonding_masters 2>/dev/null || echo 'No bonds'")
        print(stdout.read().decode('utf-8'))

        # Check bond config files
        print("\n3. Bond config file contents:")
        stdin, stdout, stderr = client.exec_command("ls /etc/sysconfig/network-scripts/ifcfg-bond* 2>/dev/null")
        bond_files = stdout.read().decode('utf-8').strip().split('\n')
        for bond_file in bond_files:
            if bond_file:
                print(f"\n--- {bond_file} ---")
                stdin, stdout, stderr = client.exec_command(f"cat {bond_file}")
                print(stdout.read().decode('utf-8'))

        # Check slave config files
        print("\n4. Checking for slave interface configs:")
        stdin, stdout, stderr = client.exec_command("grep -l 'SLAVE=yes' /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null")
        slave_files = stdout.read().decode('utf-8').strip().split('\n')
        for slave_file in slave_files:
            if slave_file:
                print(f"\n--- {slave_file} ---")
                stdin, stdout, stderr = client.exec_command(f"cat {slave_file}")
                print(stdout.read().decode('utf-8'))

        # Check current network interfaces
        print("\n5. Current network interfaces:")
        stdin, stdout, stderr = client.exec_command("ip -o link show | grep -v 'lo:'")
        print(stdout.read().decode('utf-8'))

        client.close()
        return True

    except Exception as e:
        print(f"Error connecting to {host}: {e}")
        return False

if __name__ == "__main__":
    servers = ["192.168.23.5", "192.168.23.6"]
    username = "root"
    password = "password"

    for server in servers:
        check_server(server, username, password)
