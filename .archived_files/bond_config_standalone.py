按#!/usr/bin/env python3
"""
独立的Bond配置脚本 - 直接创建配置文件
不依赖Django，直接通过SSH创建正确格式的配置
"""
import paramiko
import sys

def create_bond_config(host, ip, bond_name='bond0', mode='1', slaves=None, gateway='', dns=''):
    """在远程主机上创建Bond配置"""
    if slaves is None:
        slaves = ['ens34', 'ens35']

    print(f'\n配置 {host} (IP: {ip})...')

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='root', password='password', timeout=10)

        # 1. 清除旧配置
        print('  清除旧配置...')
        client.exec_command(f'ip link set {bond_name} down 2>/dev/null')
        client.exec_command(f'ip link delete {bond_name} 2>/dev/null')
        client.exec_command(f'rm -f /etc/sysconfig/network-scripts/ifcfg-{bond_name}')
        for slave in slaves:
            client.exec_command(f'rm -f /etc/sysconfig/network-scripts/ifcfg-{slave}')

        # 2. 创建Bond配置文件
        print(f'  创建 {bond_name} 配置...')
        bond_config = f'''cat <<EOF> /etc/sysconfig/network-scripts/ifcfg-{bond_name}
NAME="{bond_name}"
DEVICE="{bond_name}"
TYPE="Bond"
BOOTPROTO="static"
BONDING_MASTER="yes"
BONDING_OPTS="miimon=100 mode={mode}"
ONBOOT="yes"
PEERDNS="no"
IPV6INIT="no"
NM_CONTROLLED="no"
IPADDR={ip}
PREFIX=24
'''
        if gateway:
            bond_config += f'GATEWAY={gateway}\n'
        if dns:
            bond_config += f'DNS1={dns}\n'
        bond_config += 'EOF'

        stdin, stdout, stderr = client.exec_command(bond_config)
        stdout.channel.recv_exit_status()  # 等待命令完成

        # 3. 创建子接口配置文件
        for slave in slaves:
            print(f'  创建 {slave} 配置...')
            slave_config = f'''cat <<EOF> /etc/sysconfig/network-scripts/ifcfg-{slave}
NAME="{slave}"
DEVICE="{slave}"
TYPE="Ethernet"
ONBOOT="yes"
MASTER="{bond_name}"
SLAVE="yes"
NM_CONTROLLED="no"
EOF'''
            stdin, stdout, stderr = client.exec_command(slave_config)
            stdout.channel.recv_exit_status()

        # 4. 验证文件已创建
        print('  验证配置文件...')
        stdin, stdout, stderr = client.exec_command(f'test -f /etc/sysconfig/network-scripts/ifcfg-{bond_name} && echo OK || echo FAIL')
        bond_check = stdout.read().decode().strip()

        slave_checks = []
        for slave in slaves:
            stdin, stdout, stderr = client.exec_command(f'test -f /etc/sysconfig/network-scripts/ifcfg-{slave} && echo OK || echo FAIL')
            slave_checks.append(stdout.read().decode().strip())

        if bond_check == 'OK' and all(c == 'OK' for c in slave_checks):
            print(f'  [OK] 配置文件创建成功')
        else:
            print(f'  [FAIL] 配置文件创建失败: bond={bond_check}, slaves={slave_checks}')
            return False

        # 5. 重启网络服务
        print('  重启网络服务...')
        stdin, stdout, stderr = client.exec_command('systemctl restart network 2>/dev/null || service network restart 2>/dev/null')
        stdout.channel.recv_exit_status()

        client.close()
        print(f'  [OK] {host} 配置完成')
        return True

    except Exception as e:
        print(f'  [ERROR] 错误: {e}')
        return False

def verify_config(host, expected_ip):
    """验证配置结果"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='root', password='password', timeout=10)

        # 检查Bond IP
        stdin, stdout, stderr = client.exec_command('grep IPADDR /etc/sysconfig/network-scripts/ifcfg-bond0 2>/dev/null')
        ip_line = stdout.read().decode().strip()

        # 检查子接口
        stdin, stdout, stderr = client.exec_command('ls /etc/sysconfig/network-scripts/ifcfg-ens34 /etc/sysconfig/network-scripts/ifcfg-ens35 2>/dev/null | wc -l')
        slave_count = int(stdout.read().decode().strip())

        # 检查Bond slaves
        stdin, stdout, stderr = client.exec_command('cat /sys/class/net/bond0/bonding/slaves 2>/dev/null')
        active_slaves = stdout.read().decode().strip()

        # 检查Bond状态
        stdin, stdout, stderr = client.exec_command('ip addr show bond0 2>/dev/null | grep "inet " | awk \'{print $2}\'')
        active_ip = stdout.read().decode().strip()

        client.close()

        return {
            'ip_config': ip_line,
            'slave_files': slave_count,
            'active_slaves': active_slaves,
            'active_ip': active_ip,
            'success': expected_ip in ip_line and slave_count == 2
        }
    except Exception as e:
        return {'error': str(e), 'success': False}

if __name__ == '__main__':
    print('='*60)
    print('Bond配置工具 - 独立版本')
    print('='*60)

    # 配置参数
    hosts_config = [
        ('192.168.23.5', '192.168.32.7'),
        ('192.168.23.6', '192.168.32.8')
    ]

    bond_name = 'bond0'
    mode = '1'  # active-backup
    slaves = ['ens34', 'ens35']
    gateway = '192.168.32.254'

    # 应用配置
    print('\n步骤1: 应用Bond配置')
    success_count = 0
    for host, ip in hosts_config:
        if create_bond_config(host, ip, bond_name, mode, slaves, gateway):
            success_count += 1

    print(f'\n配置完成: {success_count}/{len(hosts_config)} 台成功')

    # 等待网络重启
    print('\n等待网络服务重启...')
    import time
    time.sleep(5)

    # 验证配置
    print('\n步骤2: 验证配置')
    print('='*60)
    for host, expected_ip in hosts_config:
        result = verify_config(host, expected_ip)
        print(f'\n{host}:')
        if 'error' in result:
            print(f'  错误: {result["error"]}')
        else:
            print(f'  配置IP: {result["ip_config"]}')
            print(f'  子接口文件: {result["slave_files"]}/2')
            print(f'  活动slaves: {result["active_slaves"] if result["active_slaves"] else "(无)"}')
            print(f'  活动IP: {result["active_ip"]}')
            print(f'  状态: {"[OK] 成功" if result["success"] else "[FAIL] 失败"}')

    print('\n' + '='*60)
    print('完成')
    print('='*60)
