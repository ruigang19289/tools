from django.urls import path
from . import views

urlpatterns = [
    path('connect', views.connect, name='postgres-connect'),
    path('disconnect', views.disconnect, name='postgres-disconnect'),
    path('databases', views.get_databases, name='postgres-databases'),
    path('tables', views.get_tables, name='postgres-tables'),
    path('table-info', views.get_table_info, name='postgres-table-info'),
    path('table-structure', views.get_table_structure, name='postgres-table-structure'),
    path('table-data', views.get_table_data, name='postgres-table-data'),
    path('query', views.execute_query, name='postgres-query'),
    path('schema', views.get_schema, name='postgres-schema'),
]
