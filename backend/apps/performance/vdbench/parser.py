#!/usr/bin/env python3
"""
VDBench Summary Parser
解析vdbench的summary.html文件，提取性能指标数据
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional
import os


class VDBenchParser:
    """VDBench性能数据解析器"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = {
            'metadata': {},
            'run_definitions': [],
            'performance_data': [],
            'performance_by_rd': {}  # 按run definition分组的性能数据
        }

    def parse(self) -> Dict:
        """解析summary.html文件"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 提取元数据
        self._parse_metadata(content)

        # 提取性能数据
        self._parse_performance_data(content)

        return self.data

    def _parse_metadata(self, content: str):
        """提取元数据信息"""
        # 提取创建时间
        time_match = re.search(r'created (\d{2}:\d{2}:\d{2} \w+ \d+ \d{4})', content)
        if time_match:
            self.data['metadata']['created_time'] = time_match.group(1)

        # 提取Run Definitions
        rd_pattern = r'<A HREF="#_\d+">(rd\d+[^<]+)</A>'
        rd_matches = re.findall(rd_pattern, content)
        self.data['metadata']['run_definitions'] = rd_matches

    def _parse_performance_data(self, content: str):
        """提取性能数据"""
        # 首先找到所有run definition的开始位置
        rd_pattern = r'Starting RD=(rd\d+);'
        rd_matches = list(re.finditer(rd_pattern, content))

        # 匹配标准格式的数据行
        # 格式: 时间 interval i/o_rate MB/sec bytes read_pct resp_time ...
        standard_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'

        # 匹配另一种格式的数据行（如ccc.html）
        # 格式: 时间 interval rate resp cpu_total cpu_sys read_pct read_rate read_resp write_rate write_resp mb_read mb_write mb_total xfer_size ...
        alt_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)'

        # 为每个run definition创建数据列表
        for rd_match in rd_matches:
            rd_name = rd_match.group(1)
            if rd_name not in self.data['performance_by_rd']:
                self.data['performance_by_rd'][rd_name] = []

        # 先尝试标准格式
        data_matches = list(re.finditer(standard_pattern, content))

        # 如果标准格式没有匹配到数据，尝试另一种格式
        if not data_matches:
            data_matches = list(re.finditer(alt_pattern, content))
            use_alt_format = True
        else:
            use_alt_format = False

        # 将数据点关联到对应的run definition
        for data_match in data_matches:
            match = data_match.groups()
            data_pos = data_match.start()

            # 找到这个数据点属于哪个run definition
            current_rd = None
            for i, rd_match in enumerate(rd_matches):
                if data_pos > rd_match.start():
                    current_rd = rd_match.group(1)
                    # 如果有下一个rd，检查数据点是否在下一个rd之前
                    if i + 1 < len(rd_matches):
                        if data_pos > rd_matches[i + 1].start():
                            continue
                    break

            # 如果没有找到rd标记，默认使用rd1
            if not current_rd:
                current_rd = 'rd1'
                if current_rd not in self.data['performance_by_rd']:
                    self.data['performance_by_rd'][current_rd] = []

            try:
                if use_alt_format:
                    # 另一种格式的解析
                    data_point = {
                        'rd_name': current_rd,
                        'timestamp': match[0],
                        'interval': int(match[1]),
                        'io_rate': float(match[2]),
                        'resp_time': float(match[3]),
                        'cpu_total': float(match[4]),
                        'cpu_sys': float(match[5]),
                        'read_pct': float(match[6]),
                        'read_resp': float(match[8]),
                        'write_resp': float(match[10]),
                        'mb_sec': float(match[13]),  # total MB/sec
                        'bytes_io': int(match[14]),  # xfer size
                        'read_max': 0.0,
                        'write_max': 0.0,
                        'resp_stddev': 0.0,
                        'queue_depth': 0.0
                    }
                else:
                    # 标准格式的解析
                    data_point = {
                        'rd_name': current_rd,
                        'timestamp': match[0],
                        'interval': int(match[1]),
                        'io_rate': float(match[2]),
                        'mb_sec': float(match[3]),
                        'bytes_io': int(match[4]),
                        'read_pct': float(match[5]),
                        'resp_time': float(match[6]),
                        'read_resp': float(match[7]),
                        'write_resp': float(match[8]),
                        'read_max': float(match[9]),
                        'write_max': float(match[10]),
                        'resp_stddev': float(match[11]),
                        'queue_depth': float(match[12]),
                        'cpu_total': float(match[13]),
                        'cpu_sys': float(match[14])
                    }

                self.data['performance_data'].append(data_point)

                # 同时添加到对应的rd分组中
                if current_rd:
                    self.data['performance_by_rd'][current_rd].append(data_point)
            except (ValueError, IndexError) as e:
                # 跳过无法解析的行
                continue

    def get_summary_stats(self) -> Dict:
        """计算汇总统计信息"""
        if not self.data['performance_data']:
            return {}

        # 整体统计
        perf_data = self.data['performance_data']
        io_rates = [d['io_rate'] for d in perf_data]
        mb_secs = [d['mb_sec'] for d in perf_data]
        resp_times = [d['resp_time'] for d in perf_data]
        cpu_totals = [d['cpu_total'] for d in perf_data]

        summary = {
            'total_samples': len(perf_data),
            'io_rate': {
                'avg': sum(io_rates) / len(io_rates) if io_rates else 0,
                'max': max(io_rates) if io_rates else 0,
                'min': min(io_rates) if io_rates else 0
            },
            'throughput_mb': {
                'avg': sum(mb_secs) / len(mb_secs) if mb_secs else 0,
                'max': max(mb_secs) if mb_secs else 0,
                'min': min(mb_secs) if mb_secs else 0
            },
            'response_time_ms': {
                'avg': sum(resp_times) / len(resp_times) if resp_times else 0,
                'max': max(resp_times) if resp_times else 0,
                'min': min(resp_times) if resp_times else 0
            },
            'cpu_usage_pct': {
                'avg': sum(cpu_totals) / len(cpu_totals) if cpu_totals else 0,
                'max': max(cpu_totals) if cpu_totals else 0,
                'min': min(cpu_totals) if cpu_totals else 0
            }
        }

        # 按run definition分组统计
        summary['by_run_definition'] = {}
        for rd_name, rd_data in self.data['performance_by_rd'].items():
            if not rd_data:
                continue

            # 智能判断测试类型
            test_type = self._determine_test_type(rd_data)

            rd_io_rates = [d['io_rate'] for d in rd_data]
            rd_mb_secs = [d['mb_sec'] for d in rd_data]
            rd_resp_times = [d['resp_time'] for d in rd_data]
            rd_cpu_totals = [d['cpu_total'] for d in rd_data]

            summary['by_run_definition'][rd_name] = {
                'test_type': test_type,
                'samples': len(rd_data),
                'io_rate': {
                    'avg': sum(rd_io_rates) / len(rd_io_rates) if rd_io_rates else 0,
                    'max': max(rd_io_rates) if rd_io_rates else 0,
                    'min': min(rd_io_rates) if rd_io_rates else 0
                },
                'throughput_mb': {
                    'avg': sum(rd_mb_secs) / len(rd_mb_secs) if rd_mb_secs else 0,
                    'max': max(rd_mb_secs) if rd_mb_secs else 0,
                    'min': min(rd_mb_secs) if rd_mb_secs else 0
                },
                'response_time_ms': {
                    'avg': sum(rd_resp_times) / len(rd_resp_times) if rd_resp_times else 0,
                    'max': max(rd_resp_times) if rd_resp_times else 0,
                    'min': min(rd_resp_times) if rd_resp_times else 0
                },
                'cpu_usage_pct': {
                    'avg': sum(rd_cpu_totals) / len(rd_cpu_totals) if rd_cpu_totals else 0,
                    'max': max(rd_cpu_totals) if rd_cpu_totals else 0,
                    'min': min(rd_cpu_totals) if rd_cpu_totals else 0
                }
            }

        return summary

    def _determine_test_type(self, rd_data: List[Dict]) -> str:
        """智能判断测试类型"""
        if not rd_data:
            return "未知"

        # 取第一个数据点的bytes和read_pct
        first_point = rd_data[0]
        bytes_io = first_point['bytes_io']
        read_pct = first_point['read_pct']

        # 判断IO大小
        if bytes_io >= 1048576:  # >= 1M
            # 显示为M单位
            io_size_mb = bytes_io / 1048576
            if io_size_mb == int(io_size_mb):
                io_size = f"{int(io_size_mb)}M"
            else:
                io_size = f"{io_size_mb:.1f}M"
        else:  # < 1M
            # 显示为k单位
            io_size_kb = bytes_io / 1024
            if io_size_kb == int(io_size_kb):
                io_size = f"{int(io_size_kb)}k"
            else:
                io_size = f"{io_size_kb:.0f}k"

        # 判断读写类型（四舍五入到10的倍数）
        read_pct_rounded = round(read_pct / 10) * 10

        if read_pct_rounded >= 100 or read_pct >= 99:
            rw_type = "读"
        elif read_pct_rounded <= 0 or read_pct <= 1:
            rw_type = "写"
        elif read_pct_rounded == 50:
            rw_type = "混合读写"
        else:
            rw_type = f"{int(read_pct_rounded)}%读"

        return f"{io_size}{rw_type}"

    def export_json(self, output_path: str):
        """导出为JSON格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法: python parser.py <summary.html路径>")
        sys.exit(1)

    parser = VDBenchParser(sys.argv[1])
    data = parser.parse()
    summary = parser.get_summary_stats()

    print("=" * 60)
    print("VDBench 性能数据解析结果")
    print("=" * 60)
    print(f"\n创建时间: {data['metadata'].get('created_time', 'N/A')}")
    print(f"数据点数量: {len(data['performance_data'])}")
    print(f"\n运行定义: {', '.join(data['metadata'].get('run_definitions', []))}")

    if summary:
        print("\n整体性能汇总:")
        print(f"  I/O 速率: 平均 {summary['io_rate']['avg']:.2f}, "
              f"最大 {summary['io_rate']['max']:.2f}, "
              f"最小 {summary['io_rate']['min']:.2f} IOPS")
        print(f"  吞吐量: 平均 {summary['throughput_mb']['avg']:.2f}, "
              f"最大 {summary['throughput_mb']['max']:.2f}, "
              f"最小 {summary['throughput_mb']['min']:.2f} MB/s")
        print(f"  响应时间: 平均 {summary['response_time_ms']['avg']:.2f}, "
              f"最大 {summary['response_time_ms']['max']:.2f}, "
              f"最小 {summary['response_time_ms']['min']:.2f} ms")
        print(f"  CPU 使用率: 平均 {summary['cpu_usage_pct']['avg']:.2f}, "
              f"最大 {summary['cpu_usage_pct']['max']:.2f}, "
              f"最小 {summary['cpu_usage_pct']['min']:.2f} %")

        # 显示按run definition分组的统计
        if 'by_run_definition' in summary and summary['by_run_definition']:
            print("\n按测试场景分组统计:")
            for rd_name in sorted(summary['by_run_definition'].keys()):
                rd_stats = summary['by_run_definition'][rd_name]
                print(f"\n  {rd_name} - {rd_stats['test_type']}:")
                print(f"    I/O 速率: {rd_stats['io_rate']['avg']:.2f} IOPS "
                      f"(最大: {rd_stats['io_rate']['max']:.2f}, 最小: {rd_stats['io_rate']['min']:.2f})")
                print(f"    吞吐量: {rd_stats['throughput_mb']['avg']:.2f} MB/s "
                      f"(最大: {rd_stats['throughput_mb']['max']:.2f}, 最小: {rd_stats['throughput_mb']['min']:.2f})")
                print(f"    响应时间: {rd_stats['response_time_ms']['avg']:.2f} ms "
                      f"(最大: {rd_stats['response_time_ms']['max']:.2f}, 最小: {rd_stats['response_time_ms']['min']:.2f})")
                print(f"    CPU 使用率: {rd_stats['cpu_usage_pct']['avg']:.2f}% "
                      f"(最大: {rd_stats['cpu_usage_pct']['max']:.2f}, 最小: {rd_stats['cpu_usage_pct']['min']:.2f})")

    # 导出JSON
    output_file = sys.argv[1].replace('.html', '.json')
    parser.export_json(output_file)
    print(f"\n数据已导出到: {output_file}")
