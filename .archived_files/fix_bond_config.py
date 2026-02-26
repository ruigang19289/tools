#!/usr/bin/env python3
"""
直接修复 views.py 中的 create_bond_interface 函数
使用用户提供的正确配置文件格式
"""
import re

# 读取文件
with open('backend/apps/network/bond/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到并替换 bond 配置部分
old_bond_config = r'bond_config_content = f"""DEVICE={bond_name}\nTYPE=Bond\nBONDING_MASTER=yes\nBOOTPROTO=none'

new_bond_config = '''bond_config_content = f"""NAME=\\"{bond_name}\\"
DEVICE=\\"{bond_name}\\"
TYPE=\\"Bond\\"
BOOTPROTO=\\"static\\"
BONDING_MASTER=\\"yes\\"
BONDING_OPTS=\\"miimon=100 mode={mode}\\"
ONBOOT=\\"yes\\"
PEERDNS=\\"no\\"
IPV6INIT=\\"no\\"
NM_CONTROLLED=\\"no\\"
IPADDR={ip.split('/')[0] if ip else ''}
PREFIX={ip.split('/')[1] if ip and '/' in ip else '24'}
"""

        if gateway:
            bond_config_content += f"GATEWAY={gateway}\\n"

        if dns:
            bond_config_content += f"DNS1={dns.split(',')[0].strip()}\\n"

        execute_ssh_command(client, f"cat > /etc/sysconfig/network-scripts/ifcfg-{bond_name} <<'EOF'\\n{bond_config_content}EOF")'''

# 替换
if 'BOOTPROTO=none' in content:
    # 找到 bond_config_content 的开始
    start = content.find('bond_config_content = f"""DEVICE={bond_name}')
    if start != -1:
        # 找到这个配置块的结束 (下一个 execute_ssh_command)
        end = content.find('execute_ssh_command(client, f"cat > /etc/sysconfig/network-scripts/ifcfg-{bond_name}', start)
        if end != -1:
            # 找到这行的结束
            end = content.find('\n', end + 100)

            # 替换
            before = content[:start]
            after = content[end:]
            content = before + new_bond_config + after

            print("已替换 Bond 配置格式")
        else:
            print("错误: 找不到配置块结束")
    else:
        print("错误: 找不到配置块开始")
else:
    print("配置已经是新格式或找不到旧格式")

# 替换 slave 配置部分
old_slave_pattern = r'nic_config_content = f"""DEVICE={nic}\nTYPE=Ethernet\nBOOTPROTO=none'

if 'nic_config_content = f"""DEVICE={nic}' in content:
    # 找到 slave 配置
    start = content.find('nic_config_content = f"""DEVICE={nic}')
    if start != -1:
        # 找到这个配置块的结束
        end = content.find('"""', start + 50)
        if end != -1:
            end += 3  # 包含 """

            new_slave_config = '''nic_config_content = f"""NAME=\\"{nic}\\"
DEVICE=\\"{nic}\\"
TYPE=\\"Ethernet\\"
ONBOOT=\\"yes\\"
MASTER=\\"{bond_name}\\"
SLAVE=\\"yes\\"
NM_CONTROLLED=\\"no\\"
"""'''

            before = content[:start]
            after = content[end:]
            content = before + new_slave_config + after

            print("已替换 Slave 配置格式")

# 写回文件
with open('backend/apps/network/bond/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成！")
