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

        # ping 和 setup 模块不需要命令
        if not hosts or (module not in ['ping', 'setup'] and not command):
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
    """执行 Playbook"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        playbook = data.get('playbook', '')

        if not hosts or not playbook:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表和 Playbook'}, status=400)

        # 解析 Playbook
        tasks = parse_playbook(playbook)
        
        if not tasks:
            return JsonResponse({'status': 'error', 'error': '无法解析 Playbook，请检查格式'}, status=400)

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
            
            host_result = {
                'ip': ip,
                'success': True,
                'tasks': []
            }
            
            if not password:
                host_result['success'] = False
                host_result['error'] = '需要提供密码'
                results.append(host_result)
                continue
            
            ssh, error = ssh_connect(ip, port, username, password)
            if not ssh:
                host_result['success'] = False
                host_result['error'] = f'连接失败: {error}'
                results.append(host_result)
                continue
            
            try:
                # 执行每个任务
                for task in tasks:
                    task_name = task.get('name', 'Unnamed task')
                    task_module = task.get('module', 'shell')
                    task_cmd = task.get('command', '')
                    
                    # 根据模块构造命令
                    if task_module == 'shell' or task_module == 'command':
                        cmd = task_cmd
                    elif task_module == 'yum':
                        pkg = task.get('name', '')
                        state = task.get('state', 'present')
                        if state == 'present':
                            cmd = f'yum install -y {pkg}'
                        else:
                            cmd = f'yum remove -y {pkg}'
                    elif task_module == 'copy':
                        src = task.get('src', '')
                        dest = task.get('dest', '')
                        cmd = f'cp {src} {dest}'
                    elif task_module == 'file':
                        path = task.get('path', '')
                        mode = task.get('mode', '')
                        state = task.get('state', 'file')
                        if state == 'directory':
                            cmd = f'mkdir -p {path}'
                            if mode:
                                cmd += f' && chmod {mode} {path}'
                        else:
                            cmd = f'touch {path}'
                            if mode:
                                cmd += f' && chmod {mode} {path}'
                    elif task_module == 'service':
                        name = task.get('name', '')
                        state = task.get('state', 'started')
                        if state == 'started':
                            cmd = f'systemctl start {name}'
                        elif state == 'stopped':
                            cmd = f'systemctl stop {name}'
                        elif state == 'restarted':
                            cmd = f'systemctl restart {name}'
                        else:
                            cmd = f'systemctl enable {name}'
                    elif task_module == 'cron':
                        name = task.get('name', '')
                        minute = task.get('minute', '*')
                        hour = task.get('hour', '*')
                        job = task.get('job', '')
                        cmd = f'(crontab -l 2>/dev/null | grep -v "{name}"; echo "{minute} {hour} * * * {job}") | crontab -'
                    else:
                        cmd = task_cmd if task_cmd else f'echo "Unknown module: {task_module}"'
                    
                    # 执行命令
                    output, error, exit_code = execute_ssh_command(ssh, cmd)
                    
                    host_result['tasks'].append({
                        'name': task_name,
                        'module': task_module,
                        'success': exit_code == 0,
                        'output': output or error
                    })
                    
                    # 如果任务失败，继续执行但不中断
                    if exit_code != 0:
                        host_result['success'] = False
                        
            except Exception as e:
                host_result['success'] = False
                host_result['error'] = str(e)
            finally:
                ssh.close()
                results.append(host_result)

        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


def parse_playbook(playbook_text):
    """解析 Playbook 文本，提取任务"""
    tasks = []
    lines = playbook_text.split('\n')
    
    current_task = None
    current_indent = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        indent = len(line) - len(line.lstrip())
        
        # 任务开始
        if stripped.startswith('- name:'):
            if current_task:
                tasks.append(current_task)
            current_task = {
                'name': stripped.replace('- name:', '').strip(),
                'module': 'shell',
                'command': ''
            }
            current_indent = indent
        # 模块
        elif stripped.startswith('- ') and current_task:
            module_name = stripped.replace('- ', '').replace(':', '').strip()
            current_task['module'] = module_name
        # 模块属性
        elif stripped.startswith('name:') and current_task and current_task.get('module') != 'shell':
            if current_task.get('module') in ['yum', 'copy', 'file', 'service', 'cron']:
                current_task['name'] = stripped.replace('name:', '').strip()
        elif stripped.startswith('state:') and current_task:
            current_task['state'] = stripped.replace('state:', '').strip()
        elif stripped.startswith('src:') and current_task and current_task.get('module') == 'copy':
            current_task['src'] = stripped.replace('src:', '').strip()
        elif stripped.startswith('dest:') and current_task and current_task.get('module') == 'copy':
            current_task['dest'] = stripped.replace('dest:', '').strip()
        elif stripped.startswith('path:') and current_task and current_task.get('module') == 'file':
            current_task['path'] = stripped.replace('path:', '').strip()
        elif stripped.startswith('mode:') and current_task and current_task.get('module') == 'file':
            current_task['mode'] = stripped.replace('mode:', '').strip()
        elif stripped.startswith('job:') and current_task and current_task.get('module') == 'cron':
            current_task['job'] = stripped.replace('job:', '').strip()
        elif stripped.startswith('minute:') and current_task and current_task.get('module') == 'cron':
            current_task['minute'] = stripped.replace('minute:', '').strip()
        elif stripped.startswith('hour:') and current_task and current_task.get('module') == 'cron':
            current_task['hour'] = stripped.replace('hour:', '').strip()
        # Shell/Command 模块的命令
        elif stripped.startswith('shell:') or stripped.startswith('command:'):
            cmd = stripped.replace('shell:', '').replace('command:', '').strip()
            if not current_task:
                current_task = {'name': 'Shell command', 'module': 'shell', 'command': cmd}
            else:
                current_task['command'] = cmd
    
    if current_task:
        tasks.append(current_task)
    
    return tasks
