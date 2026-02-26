"""
网络 Bond 配置工具 - Django 应用配置
"""
from django.apps import AppConfig


class BondConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.network_tools.bond_config'
    verbose_name = '网络 Bond 聚合配置工具'
