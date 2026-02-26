"""
网络连通性测试工具 - 后端API
基于 ping.sh 脚本实现
功能：
- 批量 Ping 测试
- 批量 SSH 连接测试
- 实时输出显示
- 结果统计
"""
import json
import subprocess
import threading
import time
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from concurrent.futures import ThreadPoolExecutor
import paramiko

# 活跃测试任务
active_tests = {}


def ssh_connect_test(host, port, username, password, timeout=5):
    """SSH 连接测试"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=port, username=username, password=password, timeout=timeout)
        ssh.close()
        return True, 'OK'
    except Exception as e:
        return False, str(e)[:100]


@csrf_exempt
@require_http_methods(["POST"])
def start_ping_test(request):
    """开始 Ping 测试"""
    try:
        data = json.loads(request.body)
        ips = data.get('ips', [])
        username = data.get('username', 'root')
        password = data.get('password', '')
        interval = int(data.get('interval', 1))
        packet_size = int(data.get('packet_size', 56))
        timeout = int(data.get('timeout', 5))

        if not ips:
            return JsonResponse({'status': 'error', 'error': '请提供IP列表'}, status=400)

        task_id = str(uuid.uuid4())

        active_tests[task_id] = {
            'id': task_id,
            'type': 'ping',
            'status': 'running',
            'output': [],
            'stats': {'online': 0, 'offline': 0, 'timeout': 0},
            'count': 0,
            'start_time': time.time()
        }

        def run_ping_test():
            count = 0
            stats = {'online': 0, 'offline': 0, 'timeout': 0}

            while active_tests[task_id]['status'] == 'running':
                count += 1
                cur_time = time.strftime('%Y-%m-%d %H:%M:%S')

                for ip in ips:
                    if active_tests[task_id]['status'] != 'running':
                        break

                    try:
                        # Ping 测试 - 根据操作系统使用不同参数
                        import platform
                        if platform.system().lower() == 'windows':
                            # Windows: -l 包大小, -n 次数, -w 超时(毫秒)
                            ping_cmd = ['ping', '-l', str(packet_size), '-n', '1', '-w', str(timeout * 1000), ip]
                        else:
                            # Linux/Unix: -s 包大小, -c 次数, -W 超时(秒)
                            ping_cmd = ['ping', '-s', str(packet_size), '-c', '1', '-W', str(timeout), ip]

                        result = subprocess.run(
                            ping_cmd,
                            capture_output=True,
                            text=True,
                            timeout=timeout + 2
                        )

                        if result.returncode == 0:
                            # 成功
                            output_line = result.stdout
                            stats['online'] += 1

                            # 提取完整的 ping 信息 - 兼容中英文 Windows 和 Linux
                            import re
                            message_parts = []

                            # 提取字节数
                            # Linux: "40 bytes from", Windows: "字节=32" 或 "bytes=32"
                            bytes_match = re.search(r'(\d+)\s+bytes\s+from', output_line, re.IGNORECASE)
                            if not bytes_match:
                                bytes_match = re.search(r'(?:bytes|字节)[=:]?\s*(\d+)', output_line, re.IGNORECASE)
                            if bytes_match:
                                message_parts.append(f"{bytes_match.group(1)} bytes")

                            # 提取 icmp_seq (仅 Linux)
                            seq_match = re.search(r'icmp_seq[=:]?\s*(\d+)', output_line, re.IGNORECASE)
                            if seq_match:
                                message_parts.append(f"icmp_seq={seq_match.group(1)}")

                            # 提取 ttl (TTL=64 或 ttl=64)
                            ttl_match = re.search(r'ttl[=:]?\s*(\d+)', output_line, re.IGNORECASE)
                            if ttl_match:
                                message_parts.append(f"ttl={ttl_match.group(1)}")

                            # 提取延迟时间 (time=1ms 或 time<1ms 或 时间=1ms 或 时间<1ms)
                            time_match = re.search(r'(?:time|时间)[=<]?\s*(\d+\.?\d*)\s*ms', output_line, re.IGNORECASE)
                            if time_match:
                                message_parts.append(f"time={time_match.group(1)} ms")

                            # 提取统计信息 (英文)
                            stats_match = re.search(r'(\d+)\s+packets?\s+transmitted[,\s]+(\d+)\s+received[,\s]+(\d+)%\s+packet\s+loss', output_line, re.IGNORECASE)
                            if stats_match:
                                message_parts.append(f"{stats_match.group(1)} packets transmitted, {stats_match.group(2)} received, {stats_match.group(3)}% packet loss")
                            else:
                                # 提取统计信息 (中文: 已发送 = 1,已接收 = 1,丢失 = 0)
                                stats_match_cn = re.search(r'已发送\s*=\s*(\d+)[,，]\s*已接收\s*=\s*(\d+)[,，]\s*丢失\s*=\s*(\d+)', output_line)
                                if stats_match_cn:
                                    sent = stats_match_cn.group(1)
                                    received = stats_match_cn.group(2)
                                    lost = stats_match_cn.group(3)
                                    loss_percent = int(lost) * 100 // int(sent) if int(sent) > 0 else 0
                                    message_parts.append(f"{sent} packets transmitted, {received} received, {loss_percent}% packet loss")

                            if message_parts:
                                message = f"OK {' '.join(message_parts)}"
                            else:
                                message = 'OK'

                            log_entry = {
                                'time': cur_time,
                                'type': 'success',
                                'ip': ip,
                                'count': count,
                                'message': message
                            }
                        elif result.returncode == 124:
                            # 超时
                            stats['timeout'] += 1
                            log_entry = {
                                'time': cur_time,
                                'type': 'timeout',
                                'ip': ip,
                                'count': count,
                                'message': f'TIMEOUT ({timeout}s)'
                            }
                        else:
                            # 失败
                            stats['offline'] += 1
                            log_entry = {
                                'time': cur_time,
                                'type': 'error',
                                'ip': ip,
                                'count': count,
                                'message': 'FAILED'
                            }

                        active_tests[task_id]['output'].append(log_entry)
                        # 只保留最近 500 条
                        if len(active_tests[task_id]['output']) > 500:
                            active_tests[task_id]['output'] = active_tests[task_id]['output'][-500:]

                    except Exception as e:
                        stats['offline'] += 1
                        active_tests[task_id]['output'].append({
                            'time': cur_time,
                            'type': 'error',
                            'ip': ip,
                            'count': count,
                            'message': f'ERROR: {str(e)[:50]}'
                        })

                active_tests[task_id]['stats'] = stats
                active_tests[task_id]['count'] = count

                if active_tests[task_id]['status'] == 'running':
                    time.sleep(interval)

            active_tests[task_id]['status'] = 'completed'

        thread = threading.Thread(target=run_ping_test)
        thread.start()

        return JsonResponse({
            'status': 'success',
            'task_id': task_id,
            'message': 'Ping 测试已开始'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_ssh_test(request):
    """开始 SSH 测试"""
    try:
        data = json.loads(request.body)
        ips = data.get('ips', [])
        username = data.get('username', 'root')
        password = data.get('password', '')
        interval = int(data.get('interval', 5))
        timeout = int(data.get('timeout', 5))

        if not ips:
            return JsonResponse({'status': 'error', 'error': '请提供IP列表'}, status=400)

        if not username or not password:
            return JsonResponse({'status': 'error', 'error': '请提供SSH用户名和密码'}, status=400)

        task_id = str(uuid.uuid4())

        active_tests[task_id] = {
            'id': task_id,
            'type': 'ssh',
            'status': 'running',
            'output': [],
            'stats': {'success': 0, 'failed': 0, 'timeout': 0},
            'count': 0,
            'start_time': time.time()
        }

        def run_ssh_test():
            count = 0
            stats = {'success': 0, 'failed': 0, 'timeout': 0}

            while active_tests[task_id]['status'] == 'running':
                count += 1
                cur_time = time.strftime('%Y-%m-%d %H:%M:%S')

                with ThreadPoolExecutor(max_workers=min(len(ips), 50)) as executor:
                    futures = {}
                    for ip in ips:
                        if active_tests[task_id]['status'] != 'running':
                            break
                        futures[ip] = executor.submit(ssh_connect_test, ip, 22, username, password, timeout)

                    for ip, future in futures.items():
                        if active_tests[task_id]['status'] != 'running':
                            break

                        try:
                            success, msg = future.result(timeout=timeout + 1)

                            if success:
                                stats['success'] += 1
                                log_entry = {
                                    'time': cur_time,
                                    'type': 'success',
                                    'ip': ip,
                                    'count': count,
                                    'message': 'SSH OK'
                                }
                            else:
                                if 'timed out' in msg.lower() or 'timeout' in msg.lower():
                                    stats['timeout'] += 1
                                    log_entry = {
                                        'time': cur_time,
                                        'type': 'timeout',
                                        'ip': ip,
                                        'count': count,
                                        'message': f'TIMEOUT ({timeout}s)'
                                    }
                                else:
                                    stats['failed'] += 1
                                    log_entry = {
                                        'time': cur_time,
                                        'type': 'error',
                                        'ip': ip,
                                        'count': count,
                                        'message': f'FAILED: {msg[:50]}'
                                    }

                            active_tests[task_id]['output'].append(log_entry)
                            if len(active_tests[task_id]['output']) > 500:
                                active_tests[task_id]['output'] = active_tests[task_id]['output'][-500:]

                        except Exception as e:
                            stats['failed'] += 1
                            active_tests[task_id]['output'].append({
                                'time': cur_time,
                                'type': 'error',
                                'ip': ip,
                                'count': count,
                                'message': f'ERROR: {str(e)[:50]}'
                            })

                active_tests[task_id]['stats'] = stats
                active_tests[task_id]['count'] = count

                if active_tests[task_id]['status'] == 'running':
                    time.sleep(interval)

            active_tests[task_id]['status'] = 'completed'

        thread = threading.Thread(target=run_ssh_test)
        thread.start()

        return JsonResponse({
            'status': 'success',
            'task_id': task_id,
            'message': 'SSH 测试已开始'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_test_output(request):
    """获取测试输出"""
    try:
        task_id = request.GET.get('task_id')

        if not task_id or task_id not in active_tests:
            return JsonResponse({'status': 'error', 'error': '任务不存在'}, status=404)

        task = active_tests[task_id]

        return JsonResponse({
            'status': 'success',
            'task_id': task_id,
            'type': task['type'],
            'status': task['status'],
            'count': task['count'],
            'stats': task['stats'],
            'output': task['output'][-100:]  # 最近100条
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

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
