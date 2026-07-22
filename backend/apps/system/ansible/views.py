"""
Ansible 管理平台 - 后端API
功能：
- 主机验证
- 批量命令执行
- 文件分发
- Playbook执行
"""
import json
import logging
import os
import socket
import subprocess
import tempfile
import re

import paramiko
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def ssh_connect(host, port, username, password, timeout=10):
    """SSH连接"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host,
            port=int(port),
            username=username,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        return ssh, None
    except paramiko.AuthenticationException:
        return None, '认证失败，请检查用户名或密码'
    except paramiko.SSHException as e:
        return None, f'SSH 协议错误: {e}'
    except socket.timeout:
        return None, '连接超时'
    except OSError as e:
        return None, f'网络错误: {e}'
    except Exception as e:
        logger.exception('SSH connect failed for host %s', host)
        return None, str(e)


def execute_ssh_command(ssh, command, timeout=60):
    """执行SSH命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        return output, error, stdout.channel.recv_exit_status()
    except Exception as e:
        return '', str(e), 1


def split_ansible_output_by_host(stdout, stderr, host_ips, success):
    """Split Ansible ad-hoc output so each host block only shows its own result."""
    combined = stdout or stderr or ''
    chunks = {ip: [] for ip in host_ips}
    current_ip = None
    header_re = re.compile(r'^(?P<ip>\S+)\s+\|\s+(?:SUCCESS|CHANGED|FAILED|UNREACHABLE)')

    for line in combined.splitlines():
        match = header_re.match(line)
        if match and match.group('ip') in chunks:
            current_ip = match.group('ip')
            chunks[current_ip].append(line)
        elif current_ip:
            chunks[current_ip].append(line)

    fallback = combined.strip()
    results = []
    for ip in host_ips:
        output = '\n'.join(chunks[ip]).strip() or fallback
        host_success = success and 'UNREACHABLE' not in output and 'FAILED' not in output
        results.append({'ip': ip, 'success': host_success, 'output': output})
    return results


def run_ansible_command(cmd_args):
    """执行 Ansible 命令，优先使用当前 Python 虚拟环境中的 CLI。"""
    try:
        env = os.environ.copy()
        env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        if cmd_args and cmd_args[0] == 'ansible':
            cmd_args = [os.path.join(os.path.dirname(os.sys.executable), 'ansible'), *cmd_args[1:]]
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, '', str(e)


@csrf_exempt
@require_http_methods(["POST"])
def validate_hosts(request):
    """验证主机SSH连接"""
    try:
        try:
            data = json.loads(request.body or b'{}')
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'error': f'请求 JSON 格式错误: {e}'}, status=400)

        hosts = data.get('hosts', [])
        if not isinstance(hosts, list) or not hosts:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表'}, status=400)

        results = []
        for host_info in hosts:
            if not isinstance(host_info, dict):
                results.append({
                    'ip': str(host_info),
                    'status': 'error',
                    'message': '主机参数格式错误'
                })
                continue

            ip = str(host_info.get('ip') or '').strip()
            username = str(host_info.get('username') or 'root').strip()
            password = str(host_info.get('password') or '')

            try:
                port = int(host_info.get('port') or 22)
            except (TypeError, ValueError):
                results.append({
                    'ip': ip or 'unknown',
                    'status': 'error',
                    'message': 'SSH 端口格式错误'
                })
                continue

            if not ip:
                results.append({
                    'ip': 'unknown',
                    'status': 'error',
                    'message': 'IP 不能为空'
                })
                continue

            if not password:
                results.append({
                    'ip': ip,
                    'status': 'error',
                    'message': '密码不能为空'
                })
                continue

            ssh, error = ssh_connect(ip, port, username, password)
            if ssh:
                ssh.close()
                results.append({
                    'ip': ip,
                    'status': 'success',
                    'message': '连接成功'
                })
            else:
                results.append({
                    'ip': ip,
                    'status': 'error',
                    'message': error or '连接失败'
                })

        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        logger.exception('validate_hosts failed')
        return JsonResponse({'status': 'error', 'error': f'验证接口异常: {e}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def execute_command(request):
    """批量执行命令"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        module = data.get('module', 'shell')
        command = data.get('command', '')

        # ping 和 setup 模块不需要命令
        if not hosts or (module not in ['ping', 'setup'] and not command):
            return JsonResponse({'status': 'error', 'error': '请提供主机列表和命令'}, status=400)

        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 生成 Ansible Inventory 文件
            inventory_path = os.path.join(tmpdir, 'inventory')
            with open(inventory_path, 'w') as f:
                for host_info in hosts:
                    if isinstance(host_info, str):
                        ip = host_info
                        username = 'root'
                        password = ''
                        port = 22
                    else:
                        ip = host_info.get('ip', host_info)
                        username = host_info.get('username', 'root')
                        password = host_info.get('password', '')
                        port = int(host_info.get('port', 22))
                    
                    f.write(f"{ip} ansible_user={username} ansible_ssh_pass={password} ansible_ssh_port={port} ansible_python_interpreter=/usr/bin/python3\n")
            
            # 执行 Ansible 命令
            if module == 'ping':
                cmd_args = [
                    'ansible',
                    'all',
                    '-i', inventory_path,
                    '-m', 'ping'
                ]
            elif module == 'setup':
                cmd_args = [
                    'ansible',
                    'all',
                    '-i', inventory_path,
                    '-m', 'setup'
                ]
            else:
                cmd_args = [
                    'ansible',
                    'all',
                    '-i', inventory_path,
                    '-m', module,
                    '-a', command
                ]
            
            returncode, stdout, stderr = run_ansible_command(cmd_args)
            
            # 解析结果
            host_ips = [h['ip'] if isinstance(h, dict) else h for h in hosts]
            results = split_ansible_output_by_host(stdout, stderr, host_ips, returncode == 0)
            
            return JsonResponse({'status': 'success', 'results': results})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def file_transfer(request):
    """文件分发"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        action = data.get('action', 'push')
        source = data.get('source', '')
        dest = data.get('dest', '')
        backup = data.get('backup', True)

        if not hosts or not source or not dest:
            return JsonResponse({'status': 'error', 'error': '参数不完整'}, status=400)

        results = []
        
        for host_info in hosts:
            if isinstance(host_info, str):
                ip = host_info
                username = 'root'
                password = ''
                port = 22
            else:
                ip = host_info.get('ip', host_info)
                username = host_info.get('username', 'root')
                password = host_info.get('password', '')
                port = int(host_info.get('port', 22))
            
            result = {'ip': ip, 'success': False}
            
            if not password:
                result['error'] = '需要提供密码'
                results.append(result)
                continue
            
            ssh, error = ssh_connect(ip, port, username, password)
            if not ssh:
                result['error'] = f'连接失败: {error}'
                results.append(result)
                continue
            
            try:
                if action == 'push':
                    # 推送文件 - 使用 scp
                    # 这里简化处理，实际应该使用 sftp
                    if backup:
                        execute_ssh_command(ssh, f'test -f {dest} && cp {dest} {dest}.bak || true')
                    
                    # 使用 sftp 推送文件
                    sftp = ssh.open_sftp()
                    try:
                        sftp.put(source, dest)
                        result['success'] = True
                        result['message'] = f'文件已推送到 {dest}'
                    except Exception as e:
                        result['error'] = f'推送失败: {str(e)}'
                    finally:
                        sftp.close()
                        
                elif action == 'pull':
                    # 拉取文件
                    sftp = ssh.open_sftp()
                    try:
                        sftp.get(dest, source)
                        result['success'] = True
                        result['message'] = f'文件已拉取到 {source}'
                    except Exception as e:
                        result['error'] = f'拉取失败: {str(e)}'
                    finally:
                        sftp.close()
                        
            except Exception as e:
                result['error'] = str(e)
            finally:
                ssh.close()
                results.append(result)

        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def run_playbook(request):
    """执行 Playbook"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        playbook = data.get('playbook', '')

        if not hosts or not playbook:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表和 Playbook'}, status=400)

        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 生成 Ansible Inventory 文件
            inventory_path = os.path.join(tmpdir, 'inventory')
            with open(inventory_path, 'w') as f:
                for host_info in hosts:
                    if isinstance(host_info, str):
                        ip = host_info
                        username = 'root'
                        password = ''
                        port = 22
                    else:
                        ip = host_info.get('ip', host_info)
                        username = host_info.get('username', 'root')
                        password = host_info.get('password', '')
                        port = int(host_info.get('port', 22))
                    
                    f.write(f"{ip} ansible_user={username} ansible_ssh_pass={password} ansible_ssh_port={port} ansible_python_interpreter=/usr/bin/python3\n")
            
            # 生成 Playbook 文件
            playbook_path = os.path.join(tmpdir, 'playbook.yml')
            with open(playbook_path, 'w') as f:
                f.write(playbook)
            
            # 执行 Ansible Playbook
            cmd_args = [
                'ansible-playbook',
                playbook_path,
                '-i', inventory_path,
                '-v'
            ]
            
            returncode, stdout, stderr = run_ansible_command(cmd_args)
            
            # 解析结果
            if returncode == 0:
                return JsonResponse({
                    'status': 'success',
                    'results': [{'ip': host, 'success': True, 'output': stdout} for host in [h['ip'] if isinstance(h, dict) else h for h in hosts]]
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'error': stderr or stdout
                }, status=500)
                
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


def parse_playbook(playbook_text):
    """解析 Playbook 文本，提取任务"""
    import yaml
    
    tasks = []
    try:
        # 使用 yaml 模块解析整个 Playbook
        playbook = yaml.safe_load(playbook_text)
        
        # 遍历所有 play 和任务
        for play in playbook:
            if 'tasks' in play:
                for task in play['tasks']:
                    tasks.append(task)
        
        return tasks
    except Exception as e:
        print(f"解析 Playbook 失败: {str(e)}")
        return []
