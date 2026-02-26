"""网络 Bond 配置工具 - URL 配置"""

from django.urls import path
from . import views

app_name = 'bond_config'

urlpatterns = [
    # Bond 配置生成
    path('generate/', views.generate_config, name='generate'),
    path('modes/', views.get_bond_modes, name='modes'),

    # 远程主机操作
    path('interfaces/', views.get_interfaces, name='interfaces'),
    path('apply/', views.apply_config, name='apply'),
]
