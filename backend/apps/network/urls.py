from django.urls import path, include

urlpatterns = [
    path('ping/', include('backend.apps.network.PingScan.urls')),
    path('bond/', include('backend.apps.network.bond.urls')),
    path('connection-test/', include('backend.apps.network.ConnectionTest.urls')),
    path('iperf3/', include('backend.apps.network.NetworkReliabilityTest.urls')),
]
