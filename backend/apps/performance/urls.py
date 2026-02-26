from django.urls import path, include

urlpatterns = [
    path('vdbench/', include('backend.apps.performance.vdbench.urls')),
    path('monitor/', include('backend.apps.performance.monitor.urls')),
    path('fio/', include('backend.apps.performance.FIOTest.urls')),
    path('cosbench/', include('backend.apps.performance.CosBenchGenerator.urls')),
]
