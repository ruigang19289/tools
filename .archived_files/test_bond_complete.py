#!/usr/bin/env python3
"""完整的Bond配置测试"""
import requests
import paramiko
import time

def clear_bonds(hosts):
    """清除所有Bond配置"""
    for host in hosts:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='root', password='password')
        client.exec_command('ip link set bond0 down 2>/dev/null')
        client.exec_command('ip link delete bond0 2>/dev/null')
        client.exec_command('rm -f /etc/sysconfig/network-scripts/ifcfg-bond0')
        client.exec_command('rm -f /etc/sysconfig/network-scripts/ifcfg-ens34')
        client.exec_command('rm -f /etc/sysconfig/network-scripts/ifcfg-ens35')
        client.close()
        print(f'已清除 {host} 的Bond配置')

def apply_bond_config(hosts):
    """应用Bond配置"""
    print('\n开始应用Bond配置...')
    print(f'IP范围: 192.168.32.7-192.168.32.8/24')
    print(f'预期: {hosts[0]} = .7, {hosts[1]} = .8\n')

    for idx, host in enumerate(hosts):
        print(f'[{idx}] 配置 {host}...')
        resp = requests.post('http://localhost:6000/api/v1/network/bond/apply-bond', json={
            'servers': [host],
            'server_index': idx,
            'username': 'root',
            'password': 'password',
            'bond_configs': [{
                'name': 'bond0',
                'mode': '1',
                'slaves': ['ens34', 'ens35'],
                'ip': '192.168.32.7-192.168.32.8/24',
                'gateway': '192.168.32.254',
                'dns': ''
            }]
        })

        if resp.status_code == 200:
            result = resp.json()
            if result.get('results'):
                bond_result = result['results'][0]['bonds'][0]
                print(f'    结果: {bond_result.get("success")}')
        else:
            print(f'    错误: HTTP {resp.status_code}')

        time.sleep(1)

def verify_config(hosts):
    """验证配置结果"""
    print('\n=== 验证结果 ===')

    for host in hosts:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='root', password='password')

        # 检查Bond IP
        stdin, stdout, stderr = client.exec_command('grep IPADDR /etc/sysconfig/network-scripts/ifcfg-bond0 2>/dev/null')
        bond_ip = stdout.read().decode().strip()

        # 检查子接口配置文件
        stdin, stdout, stderr = client.exec_command('test -f /etc/sysconfig/network-scripts/ifcfg-ens34 && echo YES || echo NO')
        ens34_exists = 'YES' in stdout.read().decode()

        stdin, stdout, stderr = client.exec_command('test -f /etc/sysconfig/network-scripts/ifcfg-ens35 && echo YES || echo NO')
        ens35_exists = 'YES' in stdout.read().decode()

        # 检查Bond slaves
        stdin, stdout, stderr = client.exec_command('cat /sys/class/net/bond0/bonding/slaves 2>/dev/null')
        slaves = stdout.read().decode().strip()

        print(f'\n{host}:')
        print(f'  Bond IP: {bond_ip}')
        print(f'  ens34配置: {"存在" if ens34_exists else "缺失"}')
        print(f'  ens35配置: {"存在" if ens35_exists else "缺失"}')
        print(f'  活动slaves: {slaves if slaves else "(无)"}')

        # 显示配置文件内容
        if ens34_exists:
            stdin, stdout, stderr = client.exec_command('cat /etc/sysconfig/network-scripts/ifcfg-ens34')
            print(f'\n  ens34配置内容:')
            for line in stdout.read().decode().strip().split('\n'):
                print(f'    {line}')

        client.close()

if __name__ == '__main__':
    hosts = ['192.168.23.5', '192.168.23.6']

    print('='*60)
    print('Bond配置完整测试')
    print('='*60)

    # 1. 清除现有配置
    print('\n步骤1: 清除现有Bond配置')
    clear_bonds(hosts)

    # 2. 应用新配置
    print('\n步骤2: 应用Bond配置')
    apply_bond_config(hosts)

    # 3. 验证结果
    print('\n步骤3: 验证配置')
    time.sleep(2)
    verify_config(hosts)

    print('\n'+'='*60)
    print('测试完成')
    print('='*60)
