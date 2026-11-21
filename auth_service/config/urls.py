from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('api/auth/admin/', admin.site.urls),
    path('api/auth/', include('usuarios.urls')),
]
