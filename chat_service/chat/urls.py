from django.urls import path

from . import views

urlpatterns = [
    path('conversas/', views.conversas, name='conversas'),
    path('conversas/<int:conversa_id>/mensagens/', views.mensagens, name='mensagens'),
    path('saude/', views.saude, name='saude'),
]
