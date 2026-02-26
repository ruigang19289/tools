from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.list_tests, name='vdbench-list'),
    path('load/', views.load_test, name='vdbench-load'),
    path('summary/', views.summary, name='vdbench-summary'),
    path('data/', views.data, name='vdbench-data'),
]
