"""
网络可靠性测试工具 - 后端API
基于 iperf3-bench-master 脚本实现
功能：
- One2One 测试：单服务器接收，其他服务器发送
- RoundRobin 测试：所有服务器互相发送
- 实时输出显示
"""
import json
import subprocess
import threading
import time
import uuid
import os
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import paramiko

# 活跃测试任务
active_tests = {}


def ssh_connect(host, port, username, password, timeout=10):
    """创建SSH连接"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=port, username=username, password=password, timeout=timeout)
        return ssh, None
    except Exception as e:
        return None, str(e)


def execute_ssh_command(ssh, command, timeout=60):
    """执行SSH命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        return output, error, None
    except Exception as e:
        return '', str(e), e


def get_my_ip(ssh):
    """获取本机IP"""
    output, _, _ = execute_ssh_command(ssh, "ip r get 1| grep src | head -1 | awk '{print $7}'")
    return output.strip()


def get_client_ip(ssh, server_ip):
    """获取客户端IP（到指定服务器的路径）"""
    cmd = f"ip r get {server_ip} | grep -w src"
    output, _, _ = execute_ssh_command(ssh, cmd)
    parts = output.strip().split()
    if 'via' in parts:
        idx = parts.index('via')
        if idx + 1 < len(parts):
            return parts[idx + 1]
    elif len(parts) >= 5:
        return parts[4]
    return ""


def get_server_ip_by_cidr(ssh, cidr):
    """根据CIDR获取服务器IP"""
    cmd = f"ipcalc -b {cidr} | awk -F= '{{print $2}}'"
    output, _, _ = execute_ssh_command(ssh, cmd)
    bcast = output.strip()
    if bcast:
        cmd = f"ip -4 -o a | grep ' {bcast} ' | head -1 | awk '{{print $2}}'"
        output, _, _ = execute_ssh_command(ssh, cmd)
        netdev = output.strip()
        if netdev:
            # 检查是否有bond
            cmd = f"ip l show dev {netdev} | grep -o 'master [a-zA-Z0-9-]*' | awk '{{print $2}}'"
            master, _, _ = execute_ssh_command(ssh, cmd)
            if master.strip():
                cmd = f"ifconfig {master.strip()} | grep -w inet | awk '{{print $2}}'"
            else:
                cmd = f"ifconfig {netdev} | grep -w inet | awk '{{print $2}}'"
            output, _, _ = execute_ssh_command(ssh, cmd)
            return output.strip().split('\n')[-1].strip()
    return ""


def get_peer_host(hosts, current_host):
    """获取配对主机"""
    all_hosts = hosts
    try:
        idx = all_hosts.index(current_host)
        next_idx = (idx + 1) % len(all_hosts)
        return all_hosts[next_idx]
    except ValueError:
        return None


@csrf_exempt
@require_http_methods(["POST"])
def validate_hosts(request):
    """验证主机SSH连接和iperf3可用性"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        username = data.get('username', 'root')
        password = data.get('password', '')

        if not hosts:
            return JsonResponse({'status': 'error', 'error': '请提供主机列表'}, status=400)

        results = []
        for host in hosts:
            ssh, error = ssh_connect(host, 22, username, password)

            if ssh:
                # 检查 iperf3 是否安装
                _, iperf_check, _ = execute_ssh_command(ssh, 'which iperf3')
                has_iperf3 = bool(iperf_check.strip())

                # 获取本机IP
                local_ip = get_my_ip(ssh)

                ssh.close()
                results.append({
                    'host': host,
                    'local_ip': local_ip,
                    'has_iperf3': has_iperf3,
                    'status': 'success' if has_iperf3 else 'warning',
                    'message': '连接成功' + ('，iperf3 已安装' if has_iperf3 else '，iperf3 未安装')
                })
            else:
                results.append({
                    'host': host,
                    'status': 'error',
                    'message': error
                })

        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_one2one_test(request):
    """
    开始 One2One 带宽测试
    一台服务器接收流量，其他服务器向它发送流量
    """
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        username = data.get('username', 'root')
        password = data.get('password', '')
        test_cidr = data.get('test_cidr', '')
        duration = int(data.get('duration', 10))
        parallel = int(data.get('parallel', 1))
        port = int(data.get('port', 5201))

        if not hosts or len(hosts) < 2:
            return JsonResponse({'status': 'error', 'error': '至少需要2台主机'}, status=400)

        if not test_cidr:
            return JsonResponse({'status': 'error', 'error': '请指定测试网段'}, status=400)

        task_id = str(uuid.uuid4())

        # 创建测试任务
        active_tests[task_id] = {
            'id': task_id,
            'type': 'one2one',
            'status': 'running',
            'output': [],
            'results': [],
            'start_time': time.time()
        }

        # 在后台执行测试
        def run_test():
            test_output = []
            test_results = []

            try:
                # 连接到第一台服务器作为接收端
                server_host = hosts[0]
                ssh_server, error = ssh_connect(server_host, 22, username, password)

                if not ssh_server:
                    active_tests[task_id]['status'] = 'error'
                    active_tests[task_id]['output'].append({
                        'type': 'error',
                        'time': time.strftime('%H:%M:%S'),
                        'message': f'连接服务器 {server_host} 失败: {error}'
                    })
                    return

                # 获取服务器IP
                server_ip = get_server_ip_by_cidr(ssh_server, test_cidr)
                if not server_ip:
                    server_ip = get_my_ip(ssh_server)

                test_output.append({
                    'type': 'info',
                    'time': time.strftime('%H:%M:%S'),
                    'message': f'服务器: {server_host} ({server_ip}) - 接收端'
                })

                # 为每对客户端启动测试
                for i, client_host in enumerate(hosts[1:], 1):
                    ssh_client, error = ssh_connect(client_host, 22, username, password)

                    if not ssh_client:
                        test_output.append({
                            'type': 'error',
                            'time': time.strftime('%H:%M:%S'),
                            'message': f'连接客户端 {client_host} 失败: {error}'
                        })
                        continue

                    # 获取客户端IP
                    client_ip = get_client_ip(ssh_client, server_ip)
                    if not client_ip:
                        client_ip = get_my_ip(ssh_client)

                    test_output.append({
                        'type': 'info',
                        'time': time.strftime('%H:%M:%S'),
                        'message': f'客户端 {i}: {client_host} ({client_ip}) -> {server_ip}'
                    })

                    # 启动 iperf3 服务器
                    for p in range(parallel):
                        srv_port = port + p
                        cmd = f"iperf3 -s -1 -f g -p {srv_port} | grep -w receiver &"
                        execute_ssh_command(ssh_server, cmd)

                    time.sleep(1)

                    # 启动 iperf3 客户端
                    results = []
                    for p in range(parallel):
                        client_port = port + p
                        cmd = f"iperf3 -c {server_ip} -f g -t {duration} -p {client_port} -J"
                        output, error, exc = execute_ssh_command(ssh_client, cmd, timeout=duration + 30)

                        if exc:
                            test_output.append({
                                'type': 'error',
                                'time': time.strftime('%H:%M:%S'),
                                'message': f'iperf3 错误: {str(exc)}'
                            })
                        else:
                            try:
                                result = json.loads(output)
                                bits_per_second = result.get('end', {}).get('sum_sent', {}).get('bits_per_second', 0)
                                gbps = bits_per_second / 1e9
                                results.append(gbps)
                                test_output.append({
                                    'type': 'success',
                                    'time': time.strftime('%H:%M:%S'),
                                    'message': f'  [{client_host}:{client_port}] -> {server_ip}:{port}: {gbps:.2f} Gb/s'
                                })
                            except Exception:
                                test_output.append({
                                    'type': 'info',
                                    'time': time.strftime('%H:%M:%S'),
                                    'message': f'  输出: {output[:100]}...'
                                })

                    ssh_client.close()

                    avg_gbps = sum(results) / len(results) if results else 0
                    test_results.append({
                        'client': client_host,
                        'server': server_host,
                        'avg_gbps': avg_gbps,
                        'streams': len(results)
                    })

                ssh_server.close()

                # 计算总带宽
                total_gbps = sum(r['avg_gbps'] for r in test_results)
                test_output.append({
                    'type': 'info',
                    'time': time.strftime('%H:%M:%S'),
                    'message': f'\n汇总: {total_gbps:.2f} Gb/s ({len(hosts)-1} 个客户端)'
                })

                active_tests[task_id]['status'] = 'completed'
                active_tests[task_id]['output'] = test_output
                active_tests[task_id]['results'] = test_results

            except Exception as e:
                active_tests[task_id]['status'] = 'error'
                active_tests[task_id]['output'].append({
                    'type': 'error',
                    'time': time.strftime('%H:%M:%S'),
                    'message': f'测试错误: {str(e)}'
                })

        thread = threading.Thread(target=run_test)
        thread.start()

        return JsonResponse({
            'status': 'success',
            'task_id': task_id,
            'message': 'One2One 测试已开始'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_roundrobin_test(request):
    """
    开始 RoundRobin 带宽测试
    所有服务器都参与收发
    """
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        username = data.get('username', 'root')
        password = data.get('password', '')
        test_cidr = data.get('test_cidr', '')
        duration = int(data.get('duration', 10))
        parallel = int(data.get('parallel', 1))
        port = int(data.get('port', 5201))

        if not hosts or len(hosts) < 2:
            return JsonResponse({'status': 'error', 'error': '至少需要2台主机'}, status=400)

        task_id = str(uuid.uuid4())

        active_tests[task_id] = {
            'id': task_id,
            'type': 'roundrobin',
            'status': 'running',
            'output': [],
            'results': [],
            'start_time': time.time()
        }

        def run_test():
            test_output = []
            test_results = []

            try:
                # 连接到所有服务器并启动服务
                ssh_connections = {}

                # 建立所有连接
                for host in hosts:
                    ssh, error = ssh_connect(host, 22, username, password)
                    if ssh:
                        ssh_connections[host] = ssh
                    else:
                        test_output.append({
                            'type': 'error',
                            'time': time.strftime('%H:%M:%S'),
                            'message': f'连接 {host} 失败: {error}'
                        })

                if len(ssh_connections) < 2:
                    test_output.append({
                        'type': 'error',
                        'time': time.strftime('%H:%M:%S'),
                        'message': '有效的连接数不足2台'
                    })
                    for ssh in ssh_connections.values():
                        ssh.close()
                    active_tests[task_id]['status'] = 'error'
                    active_tests[task_id]['output'] = test_output
                    return

                # 启动所有服务器
                test_output.append({
                    'type': 'info',
                    'time': time.strftime('%H:%M:%S'),
                    'message': f'启动 RoundRobin 测试 ({len(hosts)} 台服务器)'
                })

                # 获取服务器IP并配对
                server_ips = {}
                for host, ssh in ssh_connections.items():
                    if test_cidr:
                        server_ip = get_server_ip_by_cidr(ssh, test_cidr)
                    else:
                        server_ip = get_my_ip(ssh)
                    if not server_ip:
                        server_ip = get_my_ip(ssh)
                    server_ips[host] = server_ip
                    test_output.append({
                        'type': 'info',
                        'time': time.strftime('%H:%M:%S'),
                        'message': f'{host}: {server_ip}'
                    })

                # 配对测试
                for i, (sender_host, ssh_sender) in enumerate(ssh_connections.items()):
                    receiver_host = hosts[(i + 1) % len(hosts)]
                    receiver_ip = server_ips[receiver_host]

                    test_output.append({
                        'type': 'info',
                        'time': time.strftime('%H:%M:%S'),
                        'message': f'\n测试 {i+1}/{len(hosts)}: {sender_host} -> {receiver_host}'
                    })

                    # 启动服务器
                    receiver_ssh = ssh_connections[receiver_host]
                    for p in range(parallel):
                        srv_port = port + p + (i * parallel)
                        cmd = f"iperf3 -s -1 -f g -p {srv_port} | grep -w receiver &"
                        execute_ssh_command(receiver_ssh, cmd)

                    time.sleep(2)

                    # 启动客户端
                    results = []
                    sender_ip = server_ips[sender_host]
                    for p in range(parallel):
                        client_port = port + p + (i * parallel)
                        cmd = f"iperf3 -c {receiver_ip} -f g -t {duration} -p {client_port} -J"
                        output, error, exc = execute_ssh_command(ssh_sender, cmd, timeout=duration + 30)

                        if exc:
                            test_output.append({
                                'type': 'error',
                                'time': time.strftime('%H:%M:%S'),
                                'message': f'  iperf3 错误: {str(exc)}'
                            })
                        else:
                            try:
                                result = json.loads(output)
                                bits_per_second = result.get('end', {}).get('sum_sent', {}).get('bits_per_second', 0)
                                gbps = bits_per_second / 1e9
                                results.append(gbps)
                                test_output.append({
                                    'type': 'success',
                                    'time': time.strftime('%H:%M:%S'),
                                    'message': f'  {sender_ip} -> {receiver_ip}: {gbps:.2f} Gb/s'
                                })
                            except Exception as e:
                                test_output.append({
                                    'type': 'info',
                                    'time': time.strftime('%H:%M:%S'),
                                    'message': f'  输出解析失败'
                                })

                    avg_gbps = sum(results) / len(results) if results else 0
                    test_results.append({
                        'sender': sender_host,
                        'receiver': receiver_host,
                        'avg_gbps': avg_gbps,
                        'streams': len(results)
                    })

                # 关闭所有连接
                for ssh in ssh_connections.values():
                    ssh.close()

                # 汇总
                total_gbps = sum(r['avg_gbps'] for r in test_results)
                test_output.append({
                    'type': 'info',
                    'time': time.strftime('%H:%M:%S'),
                    'message': f'\n汇总: 平均 {total_gbps/len(test_results):.2f} Gb/s (共 {len(test_results)} 组)'
                })

                active_tests[task_id]['status'] = 'completed'
                active_tests[task_id]['output'] = test_output
                active_tests[task_id]['results'] = test_results

            except Exception as e:
                active_tests[task_id]['status'] = 'error'
                active_tests[task_id]['output'].append({
                    'type': 'error',
                    'time': time.strftime('%H:%M:%S'),
                    'message': f'测试错误: {str(e)}'
                })

        thread = threading.Thread(target=run_test)
        thread.start()

        return JsonResponse({
            'status': 'success',
            'task_id': task_id,
            'message': 'RoundRobin 测试已开始'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_test_output(request):
    """获取测试输出流"""
    try:
        task_id = request.GET.get('task_id')

        if not task_id or task_id not in active_tests:
            return JsonResponse({'status': 'error', 'error': '任务不存在'}, status=404)

        task = active_tests[task_id]

        # 返回所有输出
        return JsonResponse({
            'status': 'success',
            'task_id': task_id,
            'type': task['type'],
            'task_status': task['status'],
            'output': task['output'],
            'results': task.get('results', [])
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def stop_test(request):
    """停止测试"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')

        if task_id and task_id in active_tests:
            active_tests[task_id]['status'] = 'stopped'
            active_tests[task_id]['output'].append({
                'type': 'warning',
                'time': time.strftime('%H:%M:%S'),
                'message': '测试已手动停止'
            })

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
