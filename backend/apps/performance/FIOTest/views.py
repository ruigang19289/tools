import json
import uuid
import threading
import time
import logging
import asyncio
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from channels.generic.websocket import AsyncWebsocketConsumer
import paramiko

logger = logging.getLogger(__name__)

# 全局存储活动测试
active_tests = {}
active_tests_lock = threading.Lock()

# 存储 consumer 引用
fio_consumers = {}


def ssh_connect(host, username, password, port=22, timeout=10):
    """SSH 连接"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=port, username=username, password=password, timeout=timeout)
        return ssh, None
    except Exception as e:
        return None, str(e)


@csrf_exempt
@require_http_methods(["POST"])
def validate_hosts(request):
    """验证主机连接"""
    data = json.loads(request.body)
    hosts = data.get('hosts', [])
    username = data.get('username', 'root')
    password = data.get('password', '')
    port = int(data.get('port', 22) or 22)

    results = []

    for host in hosts:
        ssh, error = ssh_connect(host, username, password, port=port)
        if ssh:
            stdin, stdout, stderr = ssh.exec_command("which fio")
            has_fio = stdout.read().decode().strip() != ''

            results.append({
                'host': host,
                'status': 'success' if has_fio else 'warning',
                'message': '连接成功' + ('，FIO 已安装' if has_fio else '，FIO 未安装'),
                'has_fio': has_fio
            })
            ssh.close()
        else:
            results.append({
                'host': host,
                'status': 'error',
                'message': error or '连接失败'
            })

    return JsonResponse({'status': 'success', 'results': results})


def _send_to_consumer(task_id, message):
    """发送消息到 WebSocket consumer"""
    with active_tests_lock:
        if task_id not in active_tests:
            return
        consumer = active_tests[task_id].get('consumer')

    if consumer:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                consumer.send(text_data=json.dumps(message))
            )
            loop.close()
        except Exception as e:
            logger.error(f"Send to consumer error: {e}")


def run_fio_test(task_id, host, username, password, port, params):
    """运行 FIO 测试（后台线程）"""
    _send_to_consumer(task_id, {
        'type': 'output',
        'data': f'[{host}] 正在连接...\n'
    })

    ssh, error = ssh_connect(host, username, password, port=port)
    if not ssh:
        with active_tests_lock:
            if task_id in active_tests:
                active_tests[task_id]['failed_hosts'].append({'host': host, 'error': error})
                active_tests[task_id]['completed_hosts'] += 1
                total_hosts = len(active_tests[task_id]['hosts'])
                finished = active_tests[task_id]['completed_hosts'] >= total_hosts
                active_tests[task_id]['status'] = 'error' if finished else 'partial'
                active_tests[task_id]['error'] = error
        _send_to_consumer(task_id, {
            'type': 'output',
            'data': f'[{host}] 连接失败: {error}\n',
            'host': host
        })
        if finished:
            _send_to_consumer(task_id, {
                'type': 'error',
                'error': error,
                'host': host
            })
        return

    with active_tests_lock:
        active_tests[task_id]['status'] = 'running'

    _send_to_consumer(task_id, {
        'type': 'output',
        'data': f'[{host}] 连接成功，开始测试...\n'
    })

    ioengine = params.get('ioengine', 'libaio')
    filename = params.get('filename', '/dev/sdb')
    pool = params.get('pool', 'pool-rbdtest1')
    rw = params.get('rw', 'randread')
    rwmixread = params.get('rwmixread', 70)
    bs = params.get('bs', '4k')
    iodepth = params.get('iodepth', 64)
    numjobs = params.get('numjobs', 4)
    runtime = params.get('runtime', 60)
    size = params.get('size', '100G')
    cpus_allowed = params.get('cpus_allowed', '')

    if ioengine == 'rbd':
        cmd = f'fio --direct=1 --ioengine=rbd --pool={pool} --rbdname={filename}'
    else:
        cmd = f'fio --direct=1 --filename={filename} --ioengine=libaio'

    cmd += f' --iodepth={iodepth} --numjobs={numjobs} --rw={rw} --bs={bs}'
    if rw == 'randrw':
        cmd += f' --rwmixread={rwmixread}'
    cmd += f' --group_reporting --name=mytest --size={size}'
    cmd += ' --status-interval=1'

    if runtime:
        cmd += f' --runtime={runtime} --time_based'

    if cpus_allowed and cpus_allowed.strip():
        cmd += f' --cpus_allowed={cpus_allowed} --cpus_allowed_policy=split'

    _send_to_consumer(task_id, {
        'type': 'output',
        'data': f'[{host}] 执行命令: {cmd}\n'
    })

    output_lines = []
    test_stats = {
        'iops': 0,
        'bw_mb': 0,
        'latency_us': 0,
        'cpu_util': 0,
        'read_iops': 0,
        'write_iops': 0,
        'read_bw_mb': 0,
        'write_bw_mb': 0,
    }

    channel = ssh.get_transport().open_session()
    channel.settimeout(0.0)
    channel.exec_command(cmd)

    start_time = time.time()
    timeout = int(runtime) + 30

    try:
        while time.time() - start_time < timeout:
            with active_tests_lock:
                if task_id not in active_tests or active_tests[task_id].get('stop'):
                    break

            if channel.recv_ready():
                output = channel.recv(4096).decode('utf-8', errors='ignore')
                if output:
                    output_lines.append(output)

                    _send_to_consumer(task_id, {
                        'type': 'output',
                        'data': output,
                        'host': host
                    })

                    try:
                        import re

                        def parse_iops(value, unit):
                            unit = unit.lower()
                            if unit == 'k':
                                return value * 1000
                            if unit == 'm':
                                return value * 1000000
                            return value

                        def parse_bw_mb(value, unit):
                            if unit == 'M':
                                return value
                            if unit == 'K':
                                return value / 1024
                            if unit == 'G':
                                return value * 1024
                            return value

                        section_matches = re.findall(r'(read|write):.*?IOPS=([\d.]+)([kKmM]?).*?BW=([\d.]+)([KMG])iB/s', output, re.S)
                        if section_matches:
                            for section, iops_val, iops_unit, bw_val, bw_unit in section_matches:
                                parsed_iops = parse_iops(float(iops_val), iops_unit)
                                parsed_bw = parse_bw_mb(float(bw_val), bw_unit)
                                if section == 'read':
                                    test_stats['read_iops'] = parsed_iops
                                    test_stats['read_bw_mb'] = parsed_bw
                                elif section == 'write':
                                    test_stats['write_iops'] = parsed_iops
                                    test_stats['write_bw_mb'] = parsed_bw
                            test_stats['iops'] = test_stats['read_iops'] + test_stats['write_iops']
                            test_stats['bw_mb'] = test_stats['read_bw_mb'] + test_stats['write_bw_mb']
                        else:
                            iops_match = re.search(r'IOPS=([\d.]+)([kKmM]?)', output)
                            if iops_match:
                                test_stats['iops'] = parse_iops(float(iops_match.group(1)), iops_match.group(2))

                            bw_match = re.search(r'BW=([\d.]+)([KMG])iB/s', output)
                            if bw_match:
                                test_stats['bw_mb'] = parse_bw_mb(float(bw_match.group(1)), bw_match.group(2))

                            if rw == 'randrw':
                                test_stats['read_iops'] = test_stats['iops']
                                test_stats['read_bw_mb'] = test_stats['bw_mb']
                                test_stats['write_iops'] = 0
                                test_stats['write_bw_mb'] = 0

                        lat_match = re.search(r'\s+lat\s*\((usec|msec)\):.*?avg=([\d.]+)', output)
                        if lat_match:
                            unit = lat_match.group(1)
                            val = float(lat_match.group(2))
                            if unit == 'usec':
                                test_stats['latency_us'] = val
                            elif unit == 'msec':
                                test_stats['latency_us'] = val * 1000

                            if test_stats['iops'] > 0 or test_stats['bw_mb'] > 0:
                                with active_tests_lock:
                                    active_tests[task_id]['stats'] = test_stats.copy()

                                _send_to_consumer(task_id, {
                                    'type': 'stats',
                                    'stats': test_stats.copy(),
                                    'host': host
                                })
                    except Exception as e:
                        logger.error(f"Failed to parse FIO output: {e}")

            if channel.exit_status_ready():
                break

            time.sleep(0.1)

    except Exception as e:
        with active_tests_lock:
            active_tests[task_id]['error'] = str(e)
        _send_to_consumer(task_id, {
            'type': 'output',
            'data': f'[{host}] 错误: {str(e)}\n'
        })

    channel.close()
    ssh.close()

    final_status = 'completed'
    with active_tests_lock:
        if task_id in active_tests:
            active_tests[task_id]['completed_hosts'] += 1
            active_tests[task_id]['output'] = output_lines
            active_tests[task_id]['stats'] = test_stats
            active_tests[task_id]['completed_at'] = time.time()
            total_hosts = len(active_tests[task_id]['hosts'])
            if active_tests[task_id].get('stop'):
                final_status = 'stopped'
            elif active_tests[task_id]['completed_hosts'] < total_hosts:
                final_status = 'running'
            elif active_tests[task_id]['failed_hosts']:
                final_status = 'partial'
            active_tests[task_id]['status'] = final_status

    _send_to_consumer(task_id, {
        'type': 'output',
        'data': f'[{host}] 测试完成\n',
        'host': host
    })

    if final_status in ('completed', 'partial', 'stopped'):
        _send_to_consumer(task_id, {
            'type': 'completed',
            'stats': test_stats,
            'status': final_status
        })


@csrf_exempt
@require_http_methods(["POST"])
def start_test(request):
    """开始 FIO 测试"""
    data = json.loads(request.body)
    hosts = data.get('hosts', [])
    username = data.get('username', 'root')
    password = data.get('password', '')
    port = int(data.get('port', 22) or 22)
    test_params = data.get('params', {})

    if not hosts:
        return JsonResponse({'status': 'error', 'error': '请添加至少一台主机'}, status=400)

    task_id = str(uuid.uuid4())

    active_tests[task_id] = {
        'id': task_id,
        'hosts': hosts,
        'status': 'starting',
        'output': [],
        'stats': {},
        'stop': False,
        'start_time': time.time(),
        'completed_hosts': 0,
        'failed_hosts': [],
    }

    for i, host in enumerate(hosts):
        thread_params = test_params.copy()
        thread_params['size'] = test_params.get('size', f'{1 << (30 - i)}')

        thread = threading.Thread(
            target=run_fio_test,
            args=(task_id, host, username, password, port, thread_params)
        )
        thread.daemon = True
        thread.start()

    return JsonResponse({
        'status': 'success',
        'task_id': task_id,
        'message': f'已在 {len(hosts)} 台主机启动测试'
    })


@csrf_exempt
@require_http_methods(["POST"])
def stop_test(request):
    """停止测试"""
    data = json.loads(request.body)
    task_id = data.get('task_id')

    if task_id and task_id in active_tests:
        active_tests[task_id]['stop'] = True
        active_tests[task_id]['status'] = 'stopped'
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'error': '任务不存在'}, status=404)


@csrf_exempt
@require_http_methods(["GET"])
def get_output(request):
    """获取测试输出"""
    task_id = request.GET.get('task_id')

    if not task_id or task_id not in active_tests:
        return JsonResponse({'status': 'error', 'error': '任务不存在'}, status=404)

    test = active_tests[task_id]

    return JsonResponse({
        'status': test['status'],
        'output': test.get('output', []),
        'stats': test.get('stats', {}),
        'failed_hosts': test.get('failed_hosts', []),
        'elapsed': time.time() - test.get('start_time', time.time()),
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_results(request):
    """获取测试结果"""
    task_id = request.GET.get('task_id')

    if not task_id or task_id not in active_tests:
        return JsonResponse({'status': 'error', 'error': '任务不存在'}, status=404)

    test = active_tests[task_id]

    return JsonResponse({
        'status': test['status'],
        'stats': test.get('stats', {}),
        'failed_hosts': test.get('failed_hosts', []),
        'elapsed': time.time() - test.get('start_time', time.time()),
    })


class FIOTestConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for FIO test real-time output"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = None
        self.task_id = None

    async def connect(self):
        self.client_id = str(uuid.uuid4())
        fio_consumers[self.client_id] = self
        await self.accept()
        logger.info(f"FIO WebSocket connected: {self.client_id}")

    async def disconnect(self, close_code):
        logger.info(f"FIO WebSocket disconnected: {self.client_id}")
        fio_consumers.pop(self.client_id, None)

        if self.task_id:
            with active_tests_lock:
                if self.task_id in active_tests:
                    active_tests[self.task_id].pop('consumer', None)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'join':
                await self.handle_join(data)
            elif action == 'stop':
                await self.handle_stop(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Invalid JSON'}))
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            await self.send(text_data=json.dumps({'type': 'error', 'error': str(e)}))

    async def handle_join(self, data):
        task_id = data.get('task_id')

        if not task_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': '缺少 task_id'
            }))
            return

        with active_tests_lock:
            if task_id in active_tests:
                self.task_id = task_id
                active_tests[task_id]['consumer'] = self
                logger.info(f"WebSocket joined FIO task: {task_id}")

                await self.send(text_data=json.dumps({
                    'type': 'joined',
                    'task_id': task_id
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': '任务不存在'
                }))

    async def handle_stop(self, data):
        task_id = data.get('task_id')

        if task_id:
            with active_tests_lock:
                if task_id in active_tests:
                    active_tests[task_id]['stop'] = True
                    active_tests[task_id]['status'] = 'stopped'

            await self.send(text_data=json.dumps({
                'type': 'stopped',
                'task_id': task_id
            }))
