#!/usr/bin/env python3
"""
VDBench Summary Parser
解析vdbench的summary.html文件，提取性能指标数据
"""

import re
import json
from typing import Dict, List
import os


class VDBenchParser:
    """VDBench性能数据解析器"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = {
            'metadata': {},
            'run_definitions': [],
            'performance_data': [],
            'performance_by_rd': {}
        }

    def parse(self) -> Dict:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        self._parse_metadata(content)
        self._parse_performance_data(content)
        return self.data

    def _parse_metadata(self, content: str):
        time_match = re.search(r'created (\d{2}:\d{2}:\d{2} \w+ \d+ \d{4})', content)
        if time_match:
            self.data['metadata']['created_time'] = time_match.group(1)

        rd_pattern = r'<A HREF="#_\d+">(rd\d+[^<]+)</A>'
        rd_matches = re.findall(rd_pattern, content)
        self.data['metadata']['run_definitions'] = rd_matches

    def _parse_performance_data(self, content: str):
        rd_pattern = r'Starting RD=(rd\d+);'
        rd_matches = list(re.finditer(rd_pattern, content))

        standard_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
        alt_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)'

        for rd_match in rd_matches:
            rd_name = rd_match.group(1)
            if rd_name not in self.data['performance_by_rd']:
                self.data['performance_by_rd'][rd_name] = []

        data_matches = list(re.finditer(standard_pattern, content))
        if not data_matches:
            data_matches = list(re.finditer(alt_pattern, content))
            use_alt_format = True
        else:
            use_alt_format = False

        for data_match in data_matches:
            match = data_match.groups()
            data_pos = data_match.start()

            current_rd = None
            for i, rd_match in enumerate(rd_matches):
                if data_pos > rd_match.start():
                    current_rd = rd_match.group(1)
                    if i + 1 < len(rd_matches):
                        if data_pos > rd_matches[i + 1].start():
                            continue
                    break

            if not current_rd:
                current_rd = 'rd1'
                if current_rd not in self.data['performance_by_rd']:
                    self.data['performance_by_rd'][current_rd] = []

            try:
                if use_alt_format:
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
                        'mb_sec': float(match[13]),
                        'bytes_io': int(match[14]),
                        'read_max': 0.0,
                        'write_max': 0.0,
                        'resp_stddev': 0.0,
                        'queue_depth': 0.0
                    }
                else:
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
                self.data['performance_by_rd'][current_rd].append(data_point)
            except (ValueError, IndexError):
                continue

    def get_summary_stats(self) -> Dict:
        if not self.data['performance_data']:
            return {}

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

        summary['by_run_definition'] = {}
        for rd_name, rd_data in self.data['performance_by_rd'].items():
            if not rd_data:
                continue

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
        if not rd_data:
            return '未知'

        # 跳过预热/空样本，优先使用第一条有效性能数据判断测试类型。
        sample_point = next(
            (d for d in rd_data if d.get('bytes_io', 0) > 0 or d.get('io_rate', 0) > 0),
            rd_data[0],
        )
        bytes_io = sample_point['bytes_io']
        read_pct = sample_point['read_pct']

        if bytes_io >= 1048576:
            io_size_mb = bytes_io / 1048576
            io_size = f"{int(io_size_mb)}M" if io_size_mb == int(io_size_mb) else f"{io_size_mb:.1f}M"
        else:
            io_size_kb = bytes_io / 1024
            io_size = f"{int(io_size_kb)}k" if io_size_kb == int(io_size_kb) else f"{io_size_kb:.0f}k"

        read_pct_rounded = round(read_pct / 10) * 10
        if read_pct_rounded >= 100 or read_pct >= 99:
            rw_type = '读'
        elif read_pct_rounded <= 0 or read_pct <= 1:
            rw_type = '写'
        elif read_pct_rounded == 50:
            rw_type = '混合读写'
        else:
            rw_type = f"{int(read_pct_rounded)}%读"

        return f"{io_size}{rw_type}"
