"""
Ansible 管理平台 - 后端API
功能：
- 主机验证
- 批量命令执行
- 文件分发
- Playbook执行
"""
import json
import paramiko
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


def ssh_connect(host, port, username, password, timeout=10):
    """SSH连接"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=int(port), username=username, password=password, timeout=timeout)
        return ssh, None
    except Exception as e:
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


@csrf_exempt
@require_http_methods(["POST"])
def validate_hosts(request):
    """验证主机SSH连接"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])

        if not hosts:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表'}, status=400)

        results = []
        for host_info in hosts:
            ip = host_info.get('ip')
            username = host_info.get('username', 'root')
            password = host_info.get('password')
            port = int(host_info.get('port', 22))

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
                    'message': error
                })

        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def execute_command(request):
    """批量执行命令"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        module = data.get('module', 'shell')
        command = data.get('command', '')

        if not hosts or not command:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表和命令'}, status=400)

        results = []
        
        # 从请求中获取认证信息（简化处理，实际应该存储或重新获取）
        # 这里暂时要求在前端传入每个主机的认证信息
        
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
            
            result = {'ip': ip, 'success': False, 'output': ''}
            
            if not password:
                result['output'] = '需要提供密码'
                results.append(result)
                continue
            
            ssh, error = ssh_connect(ip, port, username, password)
            if not ssh:
                result['output'] = f'连接失败: {error}'
                results.append(result)
                continue
            
            try:
                # 根据模块执行命令
                if module == 'shell' or module == 'command':
                    cmd = command
                elif module == 'ping':
                    cmd = 'echo "pong"'
                elif module == 'setup':
                    cmd = 'hostname && uname -a && cat /etc/os-release'
                else:
                    cmd = command
                
                output, error, exit_code = execute_ssh_command(ssh, cmd)
                
                result['success'] = exit_code == 0
                result['output'] = output or error
                
            except Exception as e:
                result['output'] = str(e)
            finally:
                ssh.close()
                results.append(result)

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
    """执行 Playbook（简化版）"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        playbook = data.get('playbook', '')

        if not hosts or not playbook:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表和 Playbook'}, status=400)

        # 简化处理：将 Playbook 转换为命令执行
        output_lines = []
        output_lines.append('Playbook 执行（简化模式）')
        output_lines.append(f'目标主机: {len(hosts)} 台')
        output_lines.append('')
        
        # 解析 Playbook（简化版）
        tasks_found = []
        for line in playbook.split('\n'):
            line = line.strip()
            if line.startswith('- name:') or line.startswith('  - name:'):
                task_name = line.replace('- name:', '').replace('  - name:', '').strip()
                tasks_found.append(task_name)
        
        if tasks_found:
            output_lines.append(f'发现 {len(tasks_found)} 个任务:')
            for i, task in enumerate(tasks_found, 1):
                output_lines.append(f'  {i}. {task}')
        else:
            output_lines.append('未能解析任务，请确保 Playbook 格式正确')
        
        output_lines.append('')
        output_lines.append('提示: 完整 Playbook 执行需要安装 Ansible')

        return JsonResponse({
            'status': 'success',
            'output': '\n'.join(output_lines)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
