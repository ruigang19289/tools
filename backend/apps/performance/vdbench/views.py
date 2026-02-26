import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from config import VDBENCH_RESULT_DIR
from .parser import VDBenchParser


@csrf_exempt
def list_tests(request):
    """获取测试目录列表"""
    try:
        if not VDBENCH_RESULT_DIR.exists():
            VDBENCH_RESULT_DIR.mkdir(parents=True, exist_ok=True)
            return JsonResponse({'directories': [], 'count': 0})

        test_dirs = []
        for item in sorted(VDBENCH_RESULT_DIR.iterdir()):
            if item.is_dir():
                # 只检查 summary.html（不接受 totals.html）
                summary_path = item / 'summary.html'
                has_data = summary_path.exists()

                test_dirs.append({
                    'name': item.name,
                    'path': str(item),
                    'has_summary': has_data,
                })

        return JsonResponse({
            'directories': test_dirs,
            'count': len(test_dirs),
            'base_dir': str(VDBENCH_RESULT_DIR),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def load_test(request):
    """加载指定测试目录"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            test_name = data.get('name', '')
        except json.JSONDecodeError:
            test_name = request.GET.get('name', '')
    else:
        test_name = request.GET.get('name', '')

    if not test_name:
        return JsonResponse({'error': '测试名称不能为空'}, status=400)

    # 尝试多种路径格式
    possible_paths = [
        VDBENCH_RESULT_DIR / test_name,
        VDBENCH_RESULT_DIR / test_name.replace('_', '-'),
        VDBENCH_RESULT_DIR / test_name.replace('-', '_'),
    ]

    test_dir = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            test_dir = path
            break

    if not test_dir:
        return JsonResponse({'error': f'测试目录不存在: {test_name}'}, status=404)

    # 只检查 summary.html（不接受 totals.html）
    summary_path = test_dir / 'summary.html'
    if not summary_path.exists():
        return JsonResponse({'error': '没有找到summary.html'}, status=404)

    return JsonResponse({
        'directory': str(test_dir),
        'name': test_name,
    })


@csrf_exempt
def get_summary(request):
    """获取测试汇总数据"""
    test_name = request.GET.get('name', '')
    if not test_name:
        return JsonResponse({'error': '测试名称不能为空'}, status=400)

    # 查找测试目录
    possible_paths = [
        VDBENCH_RESULT_DIR / test_name,
        VDBENCH_RESULT_DIR / test_name.replace('_', '-'),
        VDBENCH_RESULT_DIR / test_name.replace('-', '_'),
    ]

    test_dir = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            test_dir = path
            break

    if not test_dir:
        return JsonResponse({'error': '测试不存在'}, status=404)

    # 优先使用 summary.html，如果不存在则使用 totals.html
    summary_path = test_dir / 'summary.html'
    if not summary_path.exists():
        summary_path = test_dir / 'totals.html'

    if not summary_path.exists():
        return JsonResponse({'error': 'summary.html 或 totals.html 不存在'}, status=404)

    try:
        # 解析 summary.html 或 totals.html
        parser = VDBenchParser(str(summary_path))
        data = parser.parse()
        summary = parser.get_summary_stats()

        result = {
            'metadata': data['metadata'],
            'summary': summary,
        }

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def get_data(request):
    """获取测试详细数据"""
    test_name = request.GET.get('name', '')
    if not test_name:
        return JsonResponse({'error': '测试名称不能为空'}, status=400)

    # 查找测试目录
    possible_paths = [
        VDBENCH_RESULT_DIR / test_name,
        VDBENCH_RESULT_DIR / test_name.replace('_', '-'),
        VDBENCH_RESULT_DIR / test_name.replace('-', '_'),
    ]

    test_dir = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            test_dir = path
            break

    if not test_dir:
        return JsonResponse({'error': '测试不存在'}, status=404)

    # 优先使用 summary.html，如果不存在则使用 totals.html
    summary_path = test_dir / 'summary.html'
    if not summary_path.exists():
        summary_path = test_dir / 'totals.html'

    if not summary_path.exists():
        return JsonResponse({'error': 'summary.html 或 totals.html 不存在'}, status=404)

    try:
        # 解析 summary.html 或 totals.html
        parser = VDBenchParser(str(summary_path))
        data = parser.parse()

        return JsonResponse({
            'performance_data': data['performance_data']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def summary(request):
    """兼容旧版 API: 获取汇总数据"""
    return get_summary(request)


@csrf_exempt
def data(request):
    """兼容旧版 API: 获取详细数据"""
    return get_data(request)
