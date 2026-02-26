"""
网络 Bond 配置工具 - 业务逻辑层
处理 Bond 网络聚合配置的生成和管理
"""

from typing import List, Dict
from apps.common.ssh_utils import ssh_connect, execute_ssh_command, close_ssh_client


def generate_bond_config(bond_name: str, bond_mode: str, ip_address: str,
                        netmask: str, gateway: str, interfaces: List[str],
                        mtu: int = 1500) -> str:
    """
    生成 Bond 网络配置脚本

    Args:
        bond_name: Bond 接口名称（如 bond0）
        bond_mode: Bond 模式（0-6）
        ip_address: IP 地址
        netmask: 子网掩码
        gateway: 网关
        interfaces: 物理网卡列表
        mtu: MTU 值

    Returns:
        str: 配置脚本内容
    """
    # Bond 模式说明
    bond_modes = {
        '0': 'balance-rr (轮询)',
        '1': 'active-backup (主备)',
        '2': 'balance-xor (异或)',
        '3': 'broadcast (广播)',
        '4': 'lacp (802.3ad)',
        '5': 'balance-tlb (传输负载均衡)',
        '6': 'balance-alb (自适应负载均衡)'
    }

    mode_desc = bond_modes.get(bond_mode, f'模式 {bond_mode}')

    script = f"""#!/bin/bash
# Bond 网络聚合配置脚本
# Bond 名称: {bond_name}
# Bond 模式: {mode_desc}
# IP 地址: {ip_address}/{netmask}
# 网关: {gateway}
# 物理网卡: {', '.join(interfaces)}
# MTU: {mtu}

set -e

echo "开始配置 Bond 网络聚合..."

# 1. 加载 bonding 模块
echo "加载 bonding 内核模块..."
modprobe bonding

# 2. 停止 NetworkManager（如果正在运行）
if systemctl is-active --quiet NetworkManager; then
    echo "停止 NetworkManager..."
    systemctl stop NetworkManager
    systemctl disable NetworkManager
fi

# 3. 配置物理网卡
"""

    for iface in interfaces:
        script += f"""
cat > /etc/sysconfig/network-scripts/ifcfg-{iface} << 'EOF'
DEVICE={iface}
BOOTPROTO=none
ONBOOT=yes
MASTER={bond_name}
SLAVE=yes
MTU={mtu}
EOF
"""

    script += f"""
# 4. 配置 Bond 接口
cat > /etc/sysconfig/network-scripts/ifcfg-{bond_name} << 'EOF'
DEVICE={bond_name}
TYPE=Bond
BONDING_MASTER=yes
BOOTPROTO=static
ONBOOT=yes
IPADDR={ip_address}
NETMASK={netmask}
GATEWAY={gateway}
MTU={mtu}
BONDING_OPTS="mode={bond_mode} miimon=100"
EOF

# 5. 重启网络服务
echo "重启网络服务..."
systemctl restart network

# 6. 验证配置
echo "验证 Bond 配置..."
sleep 3

if ip addr show {bond_name} | grep -q "{ip_address}"; then
    echo "✓ Bond 接口配置成功"
    echo "✓ IP 地址: {ip_address}"
else
    echo "✗ Bond 接口配置失败"
    exit 1
fi

# 显示 Bond 状态
echo ""
echo "Bond 状态信息:"
cat /proc/net/bonding/{bond_name}

echo ""
echo "Bond 网络聚合配置完成！"
"""

    return script


def get_network_interfaces(host: str, username: str, password: str, port: int = 22) -> Dict:
    """
    获取远程主机的网络接口信息

    Args:
        host: 主机地址
        username: 用户名
        password: 密码
        port: SSH 端口

    Returns:
        Dict: 包含接口列表和错误信息
    """
    client, error = ssh_connect(host, username, password, port)

    if error:
        return {'success': False, 'error': error, 'interfaces': []}

    try:
        # 获取网络接口列表（排除 lo 和虚拟接口）
        command = "ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '^bond' | grep -v '^vir'"
        stdout, stderr, exit_code = execute_ssh_command(client, command)

        if exit_code != 0:
            return {'success': False, 'error': stderr, 'interfaces': []}

        interfaces = [iface.strip() for iface in stdout.strip().split('\n') if iface.strip()]

        # 获取每个接口的详细信息
        interface_details = []
        for iface in interfaces:
            # 获取接口状态
            cmd = f"ip addr show {iface}"
            stdout, _, _ = execute_ssh_command(client, cmd)

            # 解析接口信息
            is_up = 'state UP' in stdout
            has_ip = 'inet ' in stdout

            interface_details.append({
                'name': iface,
                'status': 'UP' if is_up else 'DOWN',
                'has_ip': has_ip
            })

        close_ssh_client(client)

        return {
            'success': True,
            'interfaces': interface_details,
            'error': None
        }

    except Exception as e:
        close_ssh_client(client)
        return {'success': False, 'error': str(e), 'interfaces': []}


def apply_bond_config(host: str, username: str, password: str,
                     config_script: str, port: int = 22) -> Dict:
    """
    应用 Bond 配置到远程主机

    Args:
        host: 主机地址
        username: 用户名
        password: 密码
        config_script: 配置脚本内容
        port: SSH 端口

    Returns:
        Dict: 执行结果
    """
    client, error = ssh_connect(host, username, password, port)

    if error:
        return {'success': False, 'error': error, 'output': ''}

    try:
        # 上传脚本到临时文件
        script_path = '/tmp/bond_config.sh'
        sftp = client.open_sftp()
        with sftp.file(script_path, 'w') as f:
            f.write(config_script)
        sftp.close()

        # 添加执行权限
        execute_ssh_command(client, f'chmod +x {script_path}')

        # 执行脚本
        stdout, stderr, exit_code = execute_ssh_command(client, f'bash {script_path}', timeout=60)

        # 清理临时文件
        execute_ssh_command(client, f'rm -f {script_path}')

        close_ssh_client(client)

        output = stdout + stderr

        return {
            'success': exit_code == 0,
            'output': output,
            'error': stderr if exit_code != 0 else None
        }

    except Exception as e:
        close_ssh_client(client)
        return {'success': False, 'error': str(e), 'output': ''}
