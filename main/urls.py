from django.urls import path
from main.views import (
    api_register, api_login, api_self,
    api_courses, api_course_detail,
    api_course_modules, api_module_detail,
    api_module_complete, api_module_reorder,
    api_buy_course, api_my_courses,
    api_users, api_user_detail,
    api_user_balance, register_page,
    login_page, logout_page,
    home_page, course_detail_page,
    my_courses_page, profile_page,
    course_modules_page, download_certificate,
    mark_module_complete
    
)

app_name = 'main'

urlpatterns = [
    path('', home_page, name='home'),  
    path('register/', register_page, name='register'),
    path('login/', login_page, name='login'),  
    path('logout/', logout_page, name='logout'),
    path('course/<uuid:course_id>/', course_detail_page, name='course_detail'),
    path('profile/', profile_page, name='profile'),
    path('my-courses/', my_courses_page, name='my_courses'),
    path('course/<uuid:course_id>/modules/', course_modules_page, name='course_modules'),
    path('course/<uuid:course_id>/certificate/', download_certificate, name='download_certificate'),
    path('module/<uuid:module_id>/complete/', mark_module_complete, name='mark_module_complete'),
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