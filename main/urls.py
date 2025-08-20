from django.urls import path
from main.views import show_main, show_xml, show_json, api_register, api_login, api_self

app_name = 'main'

urlpatterns = [
    path('', show_main, name='show_main'),
    path('xml/', show_xml, name='show_xml'),
    path('json/', show_json, name='show_json'),
    path('api/auth/register', api_register, name='api_register'),
    path('api/auth/login', api_login, name='api_login'),
    path('api/auth/self', api_self, name='api_self'),
]