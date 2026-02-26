"""
Network Ping Scan Backend - Scan network for reachable hosts
"""
import json
import uuid
import ipaddress
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Global scan tasks storage
scan_tasks = {}
scan_tasks_lock = threading.Lock()


def parse_ip_range(ip_range_str):
    """
    解析IP范围字符串，返回IP列表
    支持格式：
    - 192.168.0.100-192.168.0.200 (同网段)
    - 192.168.0.100-192.168.1.200 (跨网段)
    """
    try:
        parts = ip_range_str.split('-')
        if len(parts) != 2:
            raise ValueError("IP范围格式错误，应为: IP1-IP2")

        start_ip_str = parts[0].strip()
        end_ip_str = parts[1].strip()

        start_ip = ipaddress.ip_address(start_ip_str)
        end_ip = ipaddress.ip_address(end_ip_str)

        if start_ip > end_ip:
            raise ValueError("起始IP必须小于或等于结束IP")

        ip_list = []
        current_ip = start_ip
        while current_ip <= end_ip:
            ip_list.append(current_ip)
            current_ip += 1

            if len(ip_list) > 65536:
                raise ValueError("IP范围过大，最多支持65536个IP")

        return ip_list

    except Exception as e:
        raise ValueError(f"解析IP范围失败: {str(e)}")


def parse_network_input(network_input):
    """
    解析网络输入，支持CIDR格式和IP范围
    返回IP列表
    """
    network_input = network_input.strip()

    # 检查是否是IP范围格式
    if '-' in network_input:
        return parse_ip_range(network_input)

    # 按CIDR格式处理
    try:
        network = ipaddress.ip_network(network_input, strict=False)
        hosts = list(network.hosts())

        if network.num_addresses <= 2:
            hosts = list(network)

        return hosts
    except Exception as e:
        raise ValueError(f"无效的网段格式: {str(e)}")


def ping_ip(ip, timeout=1):
    """
    Ping单个IP地址
    返回: (ip, is_alive, response_time_ms)
    """
    import platform
    import re

    try:
        start_time = time.time()

        # 检测操作系统
        is_windows = platform.system().lower() == 'windows'

        if is_windows:
            # Windows ping 命令
            # -n 1: 发送1个包
            # -w timeout*1000: 超时时间（毫秒）
            result = subprocess.run(
                ['ping', '-n', '1', '-w', str(int(timeout * 1000)), str(ip)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 0.5
            )
        else:
            # Linux/Unix ping 命令
            # -c 1: 发送1个包
            # -W timeout: 超时时间（秒）
            # -i 0.2: 间隔0.2秒
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), '-n', '-i', '0.2', str(ip)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 0.5
            )

        elapsed = (time.time() - start_time) * 1000

        if result.returncode == 0:
            output = result.stdout.decode('utf-8', errors='ignore')

            # 解析响应时间
            # Windows: time=1ms 或 time<1ms 或 时间=1ms
            # Linux: time=1.23 ms
            time_match = re.search(r'time[=<]([\d.]+)\s*ms', output, re.IGNORECASE)
            if not time_match:
                # 尝试中文格式（Windows中文系统）
                time_match = re.search(r'时间[=<]([\d.]+)\s*ms', output)

            if time_match:
                response_time = float(time_match.group(1))
            else:
                response_time = round(elapsed, 2)

            return (str(ip), True, response_time)
        else:
            return (str(ip), False, None)

    except subprocess.TimeoutExpired:
        return (str(ip), False, None)
    except Exception as e:
        print(f"Ping {ip} 失败: {e}")
        return (str(ip), False, None)


def run_scan(scan_id, network_input, timeout, max_workers=150):
    """
    执行扫描任务（在后台线程中运行）
    """
    try:
        hosts = parse_network_input(network_input)
        total = len(hosts)

        task = scan_tasks[scan_id]
        task['total'] = total
        task['status'] = 'running'

        results = []
        scanned = 0
        online = 0
        offline = 0

        # 初始化所有IP为扫描中状态
        for host in hosts:
            results.append({
                'ip': str(host),
                'status': 'scanning',
                'response_time': None
            })

        # 更新任务状态
        with scan_tasks_lock:
            task['results'] = results

        # 使用线程池并发ping
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(ping_ip, host, timeout): idx
                for idx, host in enumerate(hosts)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    ip, is_alive, response_time = future.result()

                    if is_alive:
                        results[idx]['status'] = 'online'
                        results[idx]['response_time'] = response_time
                        online += 1
                    else:
                        results[idx]['status'] = 'offline'
                        offline += 1

                    scanned += 1

                    # 更新任务状态
                    with scan_tasks_lock:
                        task['scanned'] = scanned
                        task['online'] = online
                        task['offline'] = offline
                        task['last_update'] = time.time()

                except Exception as e:
                    print(f"处理 {hosts[idx]} 时出错: {e}")
                    results[idx]['status'] = 'offline'
                    scanned += 1
                    offline += 1

                    with scan_tasks_lock:
                        task['scanned'] = scanned
                        task['offline'] = offline
                        task['last_update'] = time.time()

        # 扫描完成
        with scan_tasks_lock:
            task['status'] = 'completed'
            task['completed_at'] = time.time()

    except Exception as e:
        print(f"扫描任务 {scan_id} 出错: {e}")
        with scan_tasks_lock:
            task['status'] = 'error'
            task['error'] = str(e)


@csrf_exempt
@require_http_methods(["POST"])
def start_ping_scan(request):
    """启动网段ping扫描"""
    try:
        data = json.loads(request.body)
        network = data.get('network', '')
        timeout = data.get('timeout', 1)

        if not network:
            return JsonResponse({'error': '未指定网段或IP范围'}, status=400)

        # 解析网络输入
        try:
            hosts = parse_network_input(network)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        if len(hosts) > 65536:
            return JsonResponse({'error': 'IP数量超过限制（最多65536个）'}, status=400)

        # 创建扫描任务
        scan_id = str(uuid.uuid4())

        scan_tasks[scan_id] = {
            'scan_id': scan_id,
            'network': network,
            'timeout': timeout,
            'total': len(hosts),
            'scanned': 0,
            'online': 0,
            'offline': 0,
            'results': [],
            'status': 'initializing',
            'start_time': time.time(),
            'last_update': time.time()
        }

        # 启动后台扫描线程
        thread = threading.Thread(
            target=run_scan,
            args=(scan_id, network, timeout),
            daemon=True
        )
        thread.start()

        return JsonResponse({
            'status': 'started',
            'scan_id': scan_id,
            'network': network,
            'total': len(hosts),
            'message': '扫描已启动'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_ping_results(request, scan_id):
    """获取ping扫描结果"""
    with scan_tasks_lock:
        if scan_id not in scan_tasks:
            return JsonResponse({'error': '扫描任务不存在'}, status=404)

        task = scan_tasks[scan_id]

        return JsonResponse({
            'scan_id': scan_id,
            'network': task['network'],
            'status': task['status'],
            'results': task.get('results', []),
            'total': task['total'],
            'scanned': task['scanned'],
            'online': task['online'],
            'offline': task['offline'],
            'start_time': task['start_time'],
            'last_update': task.get('last_update', task['start_time']),
            'error': task.get('error', None)
        })


@csrf_exempt
@require_http_methods(["DELETE"])
def cancel_scan(request, scan_id):
    """取消扫描任务"""
    with scan_tasks_lock:
        if scan_id in scan_tasks:
            scan_tasks[scan_id]['status'] = 'cancelled'
            del scan_tasks[scan_id]

    return JsonResponse({'status': 'cancelled'})
