import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


def generate_controller_conf(ip_list, drivers_per_ip, start_port=18088, port_step=100):
    """生成 CosBench Controller 配置文件"""
    conf_content = "[controller]\n"
    conf_content += f"drivers = {len(ip_list) * drivers_per_ip}\n"
    conf_content += "log_level = INFO\n"
    conf_content += "log_file = log/system.log\n"
    conf_content += "archive_dir = archive\n\n"

    driver_index = 1
    for ip in ip_list:
        for i in range(drivers_per_ip):
            port = start_port + i * port_step
            conf_content += f"[driver{driver_index}]\n"
            conf_content += f"name = driver{driver_index}\n"
            conf_content += f"url = http://{ip}:{port}/driver\n\n"
            driver_index += 1

    return conf_content


def generate_start_commands(ip_list, drivers_per_ip, start_port=18088, port_step=100):
    """生成启动 Driver 的 shell 命令"""
    commands = []
    for ip in ip_list:
        for i in range(drivers_per_ip):
            port = start_port + i * port_step
            commands.append(f"./start-driver.sh 1 {ip} {port}")
    return commands


def generate_s3_workload_xml(
        workload_name,
        workload_description,
        endpoints,
        access_key,
        secret_key,
        num_drivers,
        workers_per_driver,
        total_ops,
        operation_type,
        object_size_mb,
        bucket_prefix,
        size_unit,
        object_prefix,
        read_ratio=0,
        write_ratio=100,
        path_style_access=True,
        server_side_encryption=False,
):
    """生成 S3 基准测试 XML 配置文件"""
    if operation_type == "mixed":
        return generate_mixed_workload_xml(
            workload_name, workload_description, endpoints, access_key, secret_key,
            num_drivers, workers_per_driver, total_ops, read_ratio, write_ratio,
            object_size_mb, bucket_prefix, size_unit, object_prefix,
            path_style_access, server_side_encryption
        )
    
    if operation_type not in ["read", "write"]:
        operation_type = "read"

    xml_content = f'''<?xml version="1.0" encoding="UTF-8" ?>
<workload name="{workload_name}" description="{workload_description}">
  <workflow>
    <workstage name="{operation_type}">
'''

    for driver_id in range(1, num_drivers + 1):
        endpoint = endpoints[(driver_id - 1) % len(endpoints)] if endpoints else "http://localhost:7480"
        xml_content += f'''
      <work name="w{driver_id}" workers="{workers_per_driver}" totalOps="{total_ops}" driver="driver{driver_id}">
        <operation type="{operation_type}" ratio="100" config="cprefix={bucket_prefix};oprefix={object_prefix}{driver_id:04d}-;containers=c({driver_id});objects=s(1,{total_ops});sizes=c({object_size_mb}){size_unit};" />
        <storage type="s3" config="path_style_access={'true' if path_style_access else 'false'};accesskey={access_key};secretkey={secret_key};endpoint={endpoint};server_side_encryption={'true' if server_side_encryption else 'false'};" />
      </work>
'''

    xml_content += '''    </workstage>
  </workflow>
</workload>
'''
    return xml_content


def generate_mixed_workload_xml(
        workload_name, workload_description, endpoints, access_key, secret_key,
        num_drivers, workers_per_driver, total_ops, read_ratio, write_ratio,
        object_size_mb, bucket_prefix, size_unit, object_prefix,
        path_style_access=True, server_side_encryption=False
):
    """生成读写混合的 S3 基准测试 XML 配置文件"""
    xml_content = f'''<?xml version="1.0" encoding="UTF-8" ?>
<workload name="{workload_name}" description="{workload_description}">
  <workflow>
    <workstage name="mixed">
'''

    for driver_id in range(1, num_drivers + 1):
        endpoint = endpoints[(driver_id - 1) % len(endpoints)] if endpoints else "http://localhost:7480"
        read_oprefix = f"{object_prefix}{driver_id:04d}-"
        write_oprefix = f"{object_prefix}{driver_id + 1:04d}-"
        xml_content += f'''
      <work name="w{driver_id}" workers="{workers_per_driver}" totalOps="{total_ops}" driver="driver{driver_id}">
        <operation type="read" ratio="{read_ratio}" config="cprefix={bucket_prefix};oprefix={read_oprefix};containers=c({driver_id});objects=s(1,{total_ops});sizes=c({object_size_mb}){size_unit};" />
        <operation type="write" ratio="{write_ratio}" config="cprefix={bucket_prefix};oprefix={write_oprefix};containers=c({driver_id});objects=s(1,{total_ops});sizes=c({object_size_mb}){size_unit};" />
        <storage type="s3" config="path_style_access={'true' if path_style_access else 'false'};accesskey={access_key};secretkey={secret_key};endpoint={endpoint};server_side_encryption={'true' if server_side_encryption else 'false'};" />
      </work>
'''

    xml_content += '''    </workstage>
  </workflow>
</workload>
'''
    return xml_content


@csrf_exempt
@require_http_methods(["POST"])
def generate_config(request):
    """生成配置文件"""
    data = json.loads(request.body)

    # Controller 配置
    ip_list = data.get('ip_list', [])
    drivers_per_ip = int(data.get('drivers_per_ip', 1))
    start_port = int(data.get('start_port', 18088))
    port_step = int(data.get('port_step', 100))

    # Workload 配置
    workload_name = data.get('workload_name', 's3-benchmark')
    workload_description = data.get('workload_description', 'S3 benchmark workload')
    endpoints = data.get('endpoints', [])
    access_key = data.get('access_key', '')
    secret_key = data.get('secret_key', '')
    num_drivers = int(data.get('num_drivers', 1))
    workers_per_driver = int(data.get('workers_per_driver', 100))
    total_ops = int(data.get('total_ops', 100000))
    operation_type = data.get('operation_type', 'write')
    read_ratio = int(data.get('read_ratio', 0))
    write_ratio = int(data.get('write_ratio', 100))
    object_size_mb = int(data.get('object_size_mb', 4))
    size_unit = data.get('size_unit', 'KB')
    bucket_prefix = data.get('bucket_prefix', 'test-')
    object_prefix = data.get('object_prefix', 'obj-')
    path_style_access = data.get('path_style_access', True)
    server_side_encryption = data.get('server_side_encryption', False)

    # 生成 Controller 配置
    controller_conf = generate_controller_conf(ip_list, drivers_per_ip, start_port, port_step)
    commands = generate_start_commands(ip_list, drivers_per_ip, start_port, port_step)

    # 生成启动命令
    commands_text = "\n".join(commands)

    # Controller 管理界面地址
    controller_url = f"http://{ip_list[0]}:19088/controller/index.html" if ip_list else ""

    # 生成 Workload XML
    workload_xml = generate_s3_workload_xml(
        workload_name=workload_name,
        workload_description=workload_description,
        endpoints=endpoints,
        access_key=access_key,
        secret_key=secret_key,
        num_drivers=num_drivers,
        workers_per_driver=workers_per_driver,
        total_ops=total_ops,
        operation_type=operation_type,
        object_size_mb=object_size_mb,
        bucket_prefix=bucket_prefix,
        size_unit=size_unit,
        object_prefix=object_prefix,
        read_ratio=read_ratio,
        write_ratio=write_ratio,
        path_style_access=path_style_access,
        server_side_encryption=server_side_encryption,
    )

    # 计算总 Driver 数
    total_drivers = len(ip_list) * drivers_per_ip
    port_sequence = [start_port + i * port_step for i in range(drivers_per_ip)]

    return JsonResponse({
        'status': 'success',
        'controller_conf': controller_conf,
        'start_commands': commands_text,
        'controller_url': controller_url,
        'workload_xml': workload_xml,
        'summary': {
            'total_drivers': total_drivers,
            'drivers_per_ip': drivers_per_ip,
            'ip_list': ip_list,
            'port_sequence': port_sequence,
            'total_workers': num_drivers * workers_per_driver,
        }
    })
