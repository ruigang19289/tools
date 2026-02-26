"""
SSH Terminal Backend - Real-time SSH terminal via WebSocket
Simple and reliable implementation using Django Channels
"""
import json
import uuid
import threading
import time
import logging
import paramiko
import asyncio
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# Global SSH sessions storage
ssh_sessions = {}
ssh_sessions_lock = threading.Lock()

# 存储 consumer 引用以便发送消息
consumers = {}

# Server start time for connection recovery detection
SERVER_START_TIME = time.time()


def _read_output_thread(session_id, channel):
    """Standalone function to read SSH output in a background thread"""
    import select

    while True:
        try:
            with ssh_sessions_lock:
                if session_id not in ssh_sessions:
                    break
                if channel.closed:
                    break

                # Get consumer from session
                consumer = ssh_sessions[session_id].get('consumer')

            # Use select for efficient I/O waiting (timeout 0.1s)
            readable, _, _ = select.select([channel], [], [], 0.1)

            if readable:
                try:
                    data = channel.recv(4096).decode('utf-8', errors='ignore')
                    if data and consumer:
                        try:
                            # Use asyncio to send from thread
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                consumer.send(text_data=json.dumps({
                                    'type': 'output',
                                    'session_id': session_id,
                                    'data': data
                                }))
                            )
                            loop.close()
                        except Exception as e:
                            pass  # Consumer may be disconnected
                except Exception:
                    break

        except Exception as e:
            logger.error(f"Read thread error: {e}")
            break

    # Notify consumer on close
    with ssh_sessions_lock:
        consumer = ssh_sessions.get(session_id, {}).get('consumer')

    if consumer:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                consumer.send(text_data=json.dumps({
                    'type': 'closed',
                    'session_id': session_id
                }))
            )
            loop.close()
        except Exception:
            pass


class SSHTerminalConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for SSH terminal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = None
        self.session_ids = []  # 该客户端创建的所有session

    async def connect(self):
        self.client_id = str(uuid.uuid4())
        consumers[self.client_id] = self
        await self.accept()
        logger.info(f"WebSocket connected: {self.client_id}")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: {self.client_id}")

        # 清理该客户端的所有session
        with ssh_sessions_lock:
            for session_id in self.session_ids[:]:
                if session_id in ssh_sessions:
                    session = ssh_sessions.pop(session_id)
                    try:
                        if session.get('channel'):
                            session['channel'].close()
                        if session.get('client'):
                            session['client'].close()
                    except Exception:
                        pass

        # 从consumers中移除
        consumers.pop(self.client_id, None)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'join':
                await self.handle_join(data)
            elif action == 'connect':
                await self.handle_connect(data)
            elif action == 'input':
                await self.handle_input(data)
            elif action == 'resize':
                await self.handle_resize(data)
            elif action == 'close':
                await self.handle_close(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Invalid JSON'}))
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            await self.send(text_data=json.dumps({'type': 'error', 'error': str(e)}))

    async def handle_join(self, data):
        """Handle join session request - link WebSocket to existing SSH session"""
        session_id = data.get('session_id')

        if not session_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': '缺少 session_id'
            }))
            return

        # Check if session exists
        with ssh_sessions_lock:
            if session_id in ssh_sessions:
                session = ssh_sessions[session_id]
                # Update the session with this consumer
                session['client_id'] = self.client_id
                session['consumer'] = self
                self.session_ids.append(session_id)
                logger.info(f"WebSocket joined session: {session_id}")

                # Send confirmation
                await self.send(text_data=json.dumps({
                    'type': 'joined',
                    'session_id': session_id,
                    'host': session.get('host'),
                    'username': session.get('username')
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': 'session 不存在或已过期'
                }))

    async def handle_connect(self, data):
        """Handle SSH connection"""
        host = data.get('host')
        username = data.get('username')
        password = data.get('password')
        port = int(data.get('port', 22))
        cols = int(data.get('cols', 80))
        rows = int(data.get('rows', 24))

        if not all([host, username, password]):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': '缺少必要参数'
            }))
            return

        session_id = str(uuid.uuid4())
        self.session_ids.append(session_id)

        try:
            # 创建SSH客户端
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )

            # 创建交互式shell
            channel = client.invoke_shell(term='xterm', width=cols, height=rows)
            channel.settimeout(0.0)

            # 存储session，包含consumer引用
            with ssh_sessions_lock:
                ssh_sessions[session_id] = {
                    'client': client,
                    'channel': channel,
                    'host': host,
                    'username': username,
                    'consumer': self,  # 直接存储consumer引用
                }

            # 启动读取线程
            thread = threading.Thread(
                target=_read_output_thread,
                args=(session_id, channel),
                daemon=True
            )
            thread.start()

            # 发送成功消息
            await self.send(text_data=json.dumps({
                'type': 'connected',
                'session_id': session_id,
                'host': host,
                'username': username
            }))

            logger.info(f"SSH connected: {host} -> session_id: {session_id}")

        except paramiko.AuthenticationException:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': '认证失败：用户名或密码错误'
            }))
        except Exception as e:
            logger.error(f"SSH connect error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': f'连接失败: {str(e)}'
            }))

    def _send_to_client(self, session_id, message):
        """发送消息到对应的客户端"""
        with ssh_sessions_lock:
            if session_id not in ssh_sessions:
                return
            client_id = ssh_sessions[session_id].get('client_id')

        if client_id and client_id in consumers:
            consumer = consumers[client_id]
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    consumer.send(text_data=json.dumps(message))
                )
                loop.close()
            except Exception as e:
                logger.error(f"Send to client error: {e}")

    async def handle_input(self, data):
        """处理用户输入"""
        session_id = data.get('session_id')
        input_data = data.get('data')

        with ssh_sessions_lock:
            session = ssh_sessions.get(session_id)

        if not session:
            return

        channel = session.get('channel')
        if channel and not channel.closed:
            try:
                channel.send(input_data)
            except Exception as e:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': f'发送失败: {str(e)}'
                }))

    async def handle_resize(self, data):
        """处理终端大小调整"""
        session_id = data.get('session_id')
        cols = int(data.get('cols', 80))
        rows = int(data.get('rows', 24))

        with ssh_sessions_lock:
            session = ssh_sessions.get(session_id)

        if not session:
            return

        channel = session.get('channel')
        if channel and not channel.closed:
            try:
                channel.resize_pty(width=cols, height=rows)
            except Exception as e:
                logger.error(f"Resize error: {e}")

    async def handle_close(self, data):
        """关闭SSH会话"""
        session_id = data.get('session_id')
        self._close_session(session_id)

    def _close_session(self, session_id):
        """关闭session"""
        with ssh_sessions_lock:
            session = ssh_sessions.pop(session_id, None)

        if session:
            try:
                if session.get('channel'):
                    session['channel'].close()
                if session.get('client'):
                    session['client'].close()
            except Exception as e:
                logger.error(f"Close session error: {e}")

            # 从session_ids列表中移除
            self.session_ids = [sid for sid in self.session_ids if sid != session_id]


# HTTP API endpoints
@csrf_exempt
@require_http_methods(["POST"])
def ssh_connect(request):
    """Create SSH session via HTTP API"""
    try:
        data = json.loads(request.body)
        host = data.get('host')
        username = data.get('username')
        password = data.get('password')
        port = int(data.get('port', 22))
        cols = int(data.get('cols', 80))
        rows = int(data.get('rows', 24))

        if not all([host, username, password]):
            return JsonResponse({
                'status': 'error',
                'error': '缺少必要参数'
            })

        session_id = str(uuid.uuid4())

        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )

            # Create interactive shell
            channel = client.invoke_shell(term='xterm', width=cols, height=rows)
            channel.settimeout(0.0)

            # Store session
            with ssh_sessions_lock:
                ssh_sessions[session_id] = {
                    'client': client,
                    'channel': channel,
                    'host': host,
                    'username': username,
                }

            # Start reading thread
            thread = threading.Thread(
                target=_read_output_thread,
                args=(session_id, channel),
                daemon=True
            )
            thread.start()

            logger.info(f"SSH session created: {host} -> session_id: {session_id}")

            return JsonResponse({
                'status': 'success',
                'session_id': session_id,
                'host': host,
                'username': username
            })

        except paramiko.AuthenticationException:
            return JsonResponse({
                'status': 'error',
                'error': '认证失败：用户名或密码错误'
            })
        except Exception as e:
            logger.error(f"SSH connect error: {e}")
            return JsonResponse({
                'status': 'error',
                'error': f'连接失败: {str(e)}'
            })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"SSH connect error: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ssh_disconnect(request):
    """Close SSH session via HTTP API"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')

        if not session_id:
            return JsonResponse({'status': 'error', 'error': '缺少 session_id'}, status=400)

        with ssh_sessions_lock:
            session = ssh_sessions.pop(session_id, None)

        if session:
            try:
                if session.get('channel'):
                    session['channel'].close()
                if session.get('client'):
                    session['client'].close()
                logger.info(f"SSH session closed: {session_id}")
            except Exception as e:
                logger.error(f"Close session error: {e}")

        return JsonResponse({'status': 'success'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"SSH disconnect error: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def validate_hosts(request):
    """Validate SSH connection to multiple hosts"""
    try:
        data = json.loads(request.body)
        hosts = data.get('hosts', [])
        username = data.get('username')
        password = data.get('password')
        port = int(data.get('port', 22))
        conn_type = data.get('type', 'ssh')

        if not all([hosts, username, password]):
            return JsonResponse({'status': 'error', 'error': '缺少必要参数'}, status=400)

        results = []
        for host in hosts:
            try:
                # 创建SSH客户端测试连接
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=5,
                    allow_agent=False,
                    look_for_keys=False
                )

                client.close()

                results.append({
                    'host': host,
                    'status': 'success',
                    'message': '连接成功'
                })

            except paramiko.AuthenticationException:
                results.append({
                    'host': host,
                    'status': 'error',
                    'message': '认证失败：用户名或密码错误'
                })
            except Exception as e:
                results.append({
                    'host': host,
                    'status': 'error',
                    'message': f'连接失败: {str(e)}'
                })

        return JsonResponse({
            'status': 'success',
            'results': results
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Validate hosts error: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

def parse_addresses(request):
    """解析地址输入，支持单个和范围格式"""
    try:
        data = json.loads(request.body)
        address_input = data.get('address', '').strip()

        if not address_input:
            return JsonResponse({'error': '地址不能为空'}, status=400)

        import ipaddress
        addresses = []

        # 检查范围格式 (192.168.1.5-192.168.1.8)
        if '-' in address_input:
            try:
                ip_list = parse_ip_range(address_input)
                addresses = [str(ip) for ip in ip_list]
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=400)
        else:
            # 单个地址
            try:
                ipaddress.ip_address(address_input)
                addresses = [address_input]
            except ValueError:
                return JsonResponse({'error': 'IP地址格式无效'}, status=400)

        return JsonResponse({'addresses': addresses})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def parse_ip_range(address_input):
    """解析IP范围格式"""
    import ipaddress
    addresses = []

    # 简化格式 (192.168.1.5-10)
    simple_match = re.match(r'^(\d+\.\d+\.\d+\.)(\d+)-(\d+)$', address_input)
    if simple_match:
        prefix = simple_match.group(1)
        start = int(simple_match.group(2))
        end = int(simple_match.group(3))

        if start > end:
            raise ValueError('起始IP不能大于结束IP')

        for i in range(start, end + 1):
            addresses.append(ipaddress.ip_address(prefix + str(i)))

        return addresses

    # 完整格式 (192.168.1.5-192.168.1.10)
    full_match = re.match(r'^(\d+\.\d+\.\d+\.)(\d+)-(\d+\.\d+\.\d+\.)(\d+)$', address_input)
    if full_match:
        prefix1 = full_match.group(1)
        start = int(full_match.group(2))
        prefix2 = full_match.group(3)
        end = int(full_match.group(4))

        if prefix1 != prefix2:
            raise ValueError('起始IP和结束IP必须在同一网段')

        if start > end:
            raise ValueError('起始IP不能大于结束IP')

        for i in range(start, end + 1):
            addresses.append(ipaddress.ip_address(prefix1 + str(i)))

        return addresses

    raise ValueError('无效的地址格式')


@csrf_exempt
@require_http_methods(["GET"])
def server_info(request):
    """Get server start time for connection recovery detection"""
    return JsonResponse({
        'server_start_time': SERVER_START_TIME
    })


# File Manager APIs
file_sessions = {}  # Store SFTP sessions
file_sessions_lock = threading.Lock()


def check_sftp_connection(session):
    """Check if SFTP connection is alive, reconnect if needed"""
    try:
        # Try a simple operation to check if connection is alive
        sftp = session['sftp']
        sftp.listdir('.')
        return True
    except Exception as e:
        logger.warning(f"SFTP connection check failed: {e}, attempting reconnect...")
        try:
            # Close old connection
            try:
                session['sftp'].close()
                session['client'].close()
            except:
                pass

            # Reconnect
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=session['host'],
                port=session.get('port', 22),
                username=session['username'],
                password=session['password'],
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )

            # Enable keepalive
            transport = client.get_transport()
            transport.set_keepalive(30)

            # Create new SFTP client
            sftp = client.open_sftp()
            # 不设置超时，允许大文件传输
            # sftp.get_channel().settimeout(None)

            # Update session
            session['client'] = client
            session['sftp'] = sftp

            logger.info(f"SFTP reconnected successfully for {session['host']}")
            return True
        except Exception as reconnect_error:
            logger.error(f"SFTP reconnect failed: {reconnect_error}")
            return False


@csrf_exempt
@require_http_methods(["POST"])
def file_connect(request):
    """Connect to remote host for file management using SFTP"""
    try:
        data = json.loads(request.body)
        host = data.get('host')
        username = data.get('username')
        password = data.get('password')
        port = int(data.get('port', 22))

        if not all([host, username, password]):
            return JsonResponse({'status': 'error', 'error': '缺少必要参数'}, status=400)

        session_id = str(uuid.uuid4())

        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )

            # Enable keepalive
            transport = client.get_transport()
            transport.set_keepalive(30)

            # Create SFTP client
            sftp = client.open_sftp()

            # Store session
            with file_sessions_lock:
                file_sessions[session_id] = {
                    'client': client,
                    'sftp': sftp,
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': password,
                    'current_path': '/'
                }

            logger.info(f"SFTP session created: {host}:{port} -> session_id: {session_id}")

            return JsonResponse({
                'status': 'success',
                'session_id': session_id,
                'host': host,
                'username': username
            })

        except Exception as e:
            logger.error(f"SFTP connection error: {e}")
            return JsonResponse({'status': 'error', 'error': f'连接失败: {str(e)}'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"File connect error: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def file_list(request):
    """List files in directory using SFTP"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        path = data.get('path', '/')

        with file_sessions_lock:
            session = file_sessions.get(session_id)

        if not session:
            return JsonResponse({'status': 'error', 'error': 'Session不存在或已过期'}, status=400)

        sftp = session['sftp']

        try:
            # List directory
            import stat
            files = []
            for item in sftp.listdir_attr(path):
                file_info = {
                    'name': item.filename,
                    'size': item.st_size,
                    'mtime': item.st_mtime,
                    'is_dir': stat.S_ISDIR(item.st_mode)
                }
                files.append(file_info)

            # Sort: directories first, then files
            files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

            # Update current path
            session['current_path'] = path

            return JsonResponse({
                'status': 'success',
                'path': path,
                'files': files
            })

        except Exception as e:
            logger.error(f"File list error: {e}")
            return JsonResponse({'status': 'error', 'error': f'列出文件失败: {str(e)}'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"File list error: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def file_download(request):
    """Download file using SFTP - simple and reliable"""
    try:
        session_id = request.GET.get('session_id')
        file_path = request.GET.get('path')

        logger.info(f"Download request: session={session_id}, path={file_path}")

        with file_sessions_lock:
            session = file_sessions.get(session_id)

        if not session:
            return JsonResponse({'status': 'error', 'error': 'Session不存在或已过期'}, status=400)

        if not file_path:
            return JsonResponse({'status': 'error', 'error': '缺少文件路径'}, status=400)

        sftp = session['sftp']

        # Get filename
        filename = file_path.split('/')[-1]

        logger.info(f"Starting download: {filename}")

        # Download file to memory
        import io
        file_obj = io.BytesIO()
        sftp.getfo(file_path, file_obj)
        file_obj.seek(0)

        # Send file
        from django.http import HttpResponse
        response = HttpResponse(file_obj.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(f"Download completed: {filename}")
        return response

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"File download error: {str(e)}\n{error_details}")
        return JsonResponse({'status': 'error', 'error': f'下载失败: {str(e)}'})


@csrf_exempt
@require_http_methods(["POST"])
def file_upload(request):
    """Upload file using SFTP"""
    session_id = request.POST.get('session_id')
    path = request.POST.get('path', '/')
    uploaded_file = request.FILES.get('file')

    with file_sessions_lock:
        session = file_sessions.get(session_id)

    if not session:
        return JsonResponse({'status': 'error', 'error': 'Session不存在或已过期'}, status=400)

    if not uploaded_file:
        return JsonResponse({'status': 'error', 'error': '没有上传文件'}, status=400)

    sftp = session['sftp']

    try:
        # Upload file
        remote_path = f"{path.rstrip('/')}/{uploaded_file.name}"
        sftp.putfo(uploaded_file, remote_path)

        logger.info(f"File uploaded: {remote_path}")

        return JsonResponse({
            'status': 'success',
            'message': '上传成功',
            'filename': uploaded_file.name
        })

    except Exception as e:
        logger.error(f"File upload error: {e}")
        return JsonResponse({'status': 'error', 'error': f'上传失败: {str(e)}'})


@csrf_exempt
@require_http_methods(["POST"])
def file_disconnect(request):
    """Disconnect SFTP session"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')

        with file_sessions_lock:
            session = file_sessions.pop(session_id, None)

        if session:
            try:
                if session.get('sftp'):
                    session['sftp'].close()
                if session.get('client'):
                    session['client'].close()
                logger.info(f"SFTP session closed: {session_id}")
            except Exception as e:
                logger.error(f"Close SFTP session error: {e}")

        return JsonResponse({'status': 'success'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"File disconnect error: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
