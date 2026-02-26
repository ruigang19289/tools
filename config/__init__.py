# Tools 项目配置
# ===============

# 基础目录配置
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 后端目录
BACKEND_DIR = BASE_DIR / 'backend'

# 前端目录
FRONTEND_DIR = BASE_DIR / 'frontend'

# 数据目录
DATA_DIR = BASE_DIR / 'data'
VDBENCH_RESULT_DIR = DATA_DIR / 'vdbench-result'
CACHE_DIR = DATA_DIR / 'cache'

# 日志目录
LOGS_DIR = BASE_DIR / 'logs'

# 配置目录
CONFIG_DIR = BASE_DIR / 'config'

# 确保目录存在
for dir_path in [DATA_DIR, VDBENCH_RESULT_DIR, CACHE_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
