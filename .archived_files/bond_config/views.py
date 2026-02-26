"""
网络 Bond 配置工具 - REST API 视图
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import generate_bond_config, get_network_interfaces, apply_bond_config


@api_view(['POST'])
def generate_config(request):
    """
    生成 Bond 配置脚本

    请求参数:
    - bond_name: Bond 接口名称（如 bond0）
    - bond_mode: Bond 模式（0-6）
    - ip_address: IP 地址
    - netmask: 子网掩码
    - gateway: 网关
    - interfaces: 物理网卡列表
    - mtu: MTU 值（可选，默认 1500）
    """
    required_fields = ['bond_name', 'bond_mode', 'ip_address', 'netmask', 'gateway', 'interfaces']

    # 验证必填字段
    for field in required_fields:
        if field not in request.data:
            return Response({
                'error': f'缺少参数: {field}'
            }, status=status.HTTP_400_BAD_REQUEST)

    bond_name = request.data['bond_name']
    bond_mode = request.data['bond_mode']
    ip_address = request.data['ip_address']
    netmask = request.data['netmask']
    gateway = request.data['gateway']
    interfaces = request.data['interfaces']
    mtu = request.data.get('mtu', 1500)

    # 验证接口列表
    if not isinstance(interfaces, list) or len(interfaces) < 2:
        return Response({
            'error': 'interfaces 必须是包含至少 2 个网卡的列表'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        script = generate_bond_config(
            bond_name=bond_name,
            bond_mode=bond_mode,
            ip_address=ip_address,
            netmask=netmask,
            gateway=gateway,
            interfaces=interfaces,
            mtu=mtu
        )

        return Response({
            'script': script,
            'message': 'Bond 配置脚本生成成功'
        })

    except Exception as e:
        return Response({
            'error': f'生成配置失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
def get_interfaces(request):
    """
    获取远程主机的网络接口列表

    请求参数:
    - host: 主机地址
    - username: 用户名
    - password: 密码
    - port: SSH 端口（可选，默认 22）
    """
    # 支持 GET 和 POST 两种方法
    if request.method == 'GET':
        host = request.GET.get('host')
        username = request.GET.get('username')
        password = request.GET.get('password')
        port = request.GET.get('port', 22)
    else:
        host = request.data.get('host')
        username = request.data.get('username')
        password = request.data.get('password')
        port = request.data.get('port', 22)

    if not all([host, username, password]):
        return Response({
            'error': '缺少必填参数: host, username, password'
        }, status=status.HTTP_400_BAD_REQUEST)

    result = get_network_interfaces(host, username, password, port)

    if result['success']:
        return Response({
            'host': host,
            'interfaces': result['interfaces']
        })
    else:
        return Response({
            'error': result['error']
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def apply_config(request):
    """
    应用 Bond 配置到远程主机

    请求参数:
    - host: 主机地址
    - username: 用户名
    - password: 密码
    - config_script: 配置脚本内容
    - port: SSH 端口（可选，默认 22）
    """
    host = request.data.get('host')
    username = request.data.get('username')
    password = request.data.get('password')
    config_script = request.data.get('config_script')
    port = request.data.get('port', 22)

    if not all([host, username, password, config_script]):
        return Response({
            'error': '缺少必填参数: host, username, password, config_script'
        }, status=status.HTTP_400_BAD_REQUEST)

    result = apply_bond_config(host, username, password, config_script, port)

    if result['success']:
        return Response({
            'message': 'Bond 配置应用成功',
            'output': result['output']
        })
    else:
        return Response({
            'error': result['error'],
            'output': result['output']
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_bond_modes(request):
    """获取支持的 Bond 模式列表"""
    modes = [
        {'value': '0', 'name': 'balance-rr', 'description': '轮询策略，提供负载均衡和容错'},
        {'value': '1', 'name': 'active-backup', 'description': '主备策略，只有一个网卡工作'},
        {'value': '2', 'name': 'balance-xor', 'description': 'XOR 策略，提供负载均衡和容错'},
        {'value': '3', 'name': 'broadcast', 'description': '广播策略，所有网卡发送相同数据'},
        {'value': '4', 'name': '802.3ad (LACP)', 'description': '动态链路聚合，需要交换机支持'},
        {'value': '5', 'name': 'balance-tlb', 'description': '传输负载均衡，不需要交换机支持'},
        {'value': '6', 'name': 'balance-alb', 'description': '自适应负载均衡，不需要交换机支持'}
    ]

    return Response({
        'modes': modes
    })
