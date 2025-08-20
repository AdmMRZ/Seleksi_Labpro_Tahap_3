from django.shortcuts import render, redirect
from main.models import CourseEntry
from django.http import HttpResponse, JsonResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from main.models import CourseEntry, CustomUser
import datetime, jwt
import json


SECRET_KEY = settings.SECRET_KEY

def show_main(request):
    course_entries = CourseEntry.objects.all()
    return render(request, 'main.html', {'course_entries': course_entries})

@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)
    try:
        body = json.loads(request.body)
        first_name = body.get('first_name')
        last_name = body.get('last_name')
        username = body.get('username')
        email = body.get('email')
        password = body.get('password')
        confirm_password = body.get('confirm_password')

        if not all([first_name, last_name, username, email, password, confirm_password]):
            return JsonResponse({'status': 'error', 'message': 'Semua field wajib diisi', 'data': None}, status=400)
        if password != confirm_password:
            return JsonResponse({'status': 'error', 'message': 'Password dan konfirmasi tidak sama', 'data': None}, status=400)
        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username sudah dipakai', 'data': None}, status=400)
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'Email sudah dipakai', 'data': None}, status=400)
        if len(password) < 8 or password.isalpha() or password.isnumeric():
            return JsonResponse({'status': 'error', 'message': 'Password harus minimal 8 karakter dan campuran huruf+angka', 'data': None}, status=400)

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            balance=0,
            is_administrator=False
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Register berhasil',
            'data': {
                'id': str(user.id),
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=500)

@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)
    
    try:
        body = json.loads(request.body)
        identifier = body.get('identifier')
        password = body.get('password')

        user = CustomUser.objects.filter(username=identifier).first() or CustomUser.objects.filter(email=identifier).first()
        if user is None or not user.check_password(password):
            return JsonResponse({'status': 'error', 'message': 'Username/email atau password salah', 'data': None}, status=401)
        
        payload = {
            'id': str(user.id),
            'username': user.username,
            'is_admin': user.is_administrator,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            'iat': datetime.datetime.utcnow()
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return JsonResponse({
            'status': 'success',
            'message': 'Login berhasil',
            'data': {
                'username': user.username,
                'token': token
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=500)

def get_user_from_token(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user = CustomUser.objects.filter(id=payload['id']).first()
        return user
    except Exception:
        return None

@csrf_exempt
def api_self(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)
    
    user = get_user_from_token(request)

    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    
    return JsonResponse({
        'status': 'success',
        'message': '',
        'data': {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'balance': user.balance
        }
    })

def show_xml(request):
    course_entries = CourseEntry.objects.all()
    data = serializers.serialize('xml', course_entries)
    return HttpResponse(data, content_type='application/xml')

def show_json(request):
    course_entries = CourseEntry.objects.all()
    data = serializers.serialize('json', course_entries)
    return HttpResponse(data, content_type='application/json')
