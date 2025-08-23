from django.urls import path
from main.views import (
    show_xml, show_json,
    api_register, api_login, api_self,
    api_courses, api_course_detail,
    api_course_modules, api_module_detail,
    api_module_complete, api_module_reorder,
    api_buy_course, api_my_courses,
    api_users, api_user_detail,
    api_user_balance,
)

app_name = 'main'

urlpatterns = [
    path('xml/', show_xml, name='show_xml'),
    path('json/', show_json, name='show_json'),
    path('api/auth/register', api_register, name='api_register'),
    path('api/auth/login', api_login, name='api_login'),
    path('api/auth/self', api_self, name='api_self'),
    path('api/courses', api_courses, name='api_courses'),
    path('api/courses/my-courses', api_my_courses, name='api_my_courses'),
    path('api/courses/<str:course_id>', api_course_detail, name='api_course_detail'),
    path('api/courses/<str:course_id>/modules', api_course_modules, name='api_course_modules'),
    path('api/modules/<str:module_id>', api_module_detail, name='api_module_detail'),
    path('api/modules/<str:module_id>/complete', api_module_complete, name='api_module_complete'),
    path('api/courses/<str:course_id>/modules/reorder', api_module_reorder, name='api_module_reorder'),
    path('api/courses/<str:course_id>/buy', api_buy_course, name='api_buy_course'),
    path('api/users', api_users, name='api_users'),
    path('api/users/<str:user_id>', api_user_detail, name='api_user_detail'),
    path('api/users/<str:user_id>/balance', api_user_balance, name='api_user_balance'),
]