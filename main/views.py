from django.shortcuts import render, redirect
from main.models import CourseEntry
from django.http import HttpResponse, JsonResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from main.models import CourseEntry, CustomUser, ModuleEntry, ModuleProgress, CoursePurchase
from django.db import models
import datetime, jwt
import json


SECRET_KEY = settings.SECRET_KEY

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

@csrf_exempt
def api_courses(request):
    user = get_user_from_token(request)

    if request.method == 'GET':
        q = request.GET.get('q', '')
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 15)), 50)
        courses = CourseEntry.objects.filter(
            models.Q(title__icontains=q) |
            models.Q(instructor__icontains=q) |
            models.Q(topics__icontains=q)
        ).order_by('-id')

        total_items = courses.count()
        total_pages = (total_items + limit - 1) // limit
        courses = courses[(page-1)*limit : page*limit]
        data = []

        for c in courses:
            data.append({
                "id": str(c.id),
                "title": c.title,
                "description": c.description,
                "instructor": c.instructor,
                "topics": c.topics,
                "price": c.price,
                "thumbnail_image": c.thumbnail_image,
                "total_modules": c.modules.count() if hasattr(c, 'modules') else 0,
                "created_at": c.created_at.isoformat() if hasattr(c, 'created_at') else None,
                "updated_at": c.updated_at.isoformat() if hasattr(c, 'updated_at') else None
            })

        return JsonResponse({
            "status": "success",
            "message": "",
            "data": data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_items
            }
        })

    elif request.method == 'POST':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
        try:
            body = json.loads(request.body)
            title = body.get('title')
            description = body.get('description')
            instructor = body.get('instructor')
            topics = body.get('topics', [])
            price = body.get('price')
            thumbnail_url = body.get('thumbnail_image')  

            course = CourseEntry.objects.create(
                title=title,
                description=description,
                instructor=instructor,
                topics=topics,
                price=price,
                thumbnail_image=thumbnail_url
            )
            return JsonResponse({
                "status": "success",
                "message": "Course created",
                "data": {
                    "id": str(course.id),
                    "title": course.title,
                    "description": course.description,
                    "instructor": course.instructor,
                    "topics": course.topics,
                    "price": course.price,
                    "thumbnail_image": course.thumbnail_image,
                    "created_at": course.created_at.isoformat() if hasattr(course, 'created_at') else None,
                    "updated_at": course.updated_at.isoformat() if hasattr(course, 'updated_at') else None
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)

@csrf_exempt
def api_course_detail(request, course_id):
    user = get_user_from_token(request)
    course = CourseEntry.objects.filter(id=course_id).first()
    if not course:
        return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)
    
    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "message": "",
            "data": {
                "id": str(course.id),
                "title": course.title,
                "description": course.description,
                "instructor": course.instructor,
                "topics": course.topics,
                "price": course.price,
                "thumbnail_image": course.thumbnail_image,
                "total_modules": course.modules.count() if hasattr(course, 'modules') else 0,
                "created_at": course.created_at.isoformat() if hasattr(course, 'created_at') else None,
                "updated_at": course.updated_at.isoformat() if hasattr(course, 'updated_at') else None
            }
        })
    
    elif request.method == 'PUT':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
        try:
            body = json.loads(request.body)
            title = body.get('title', course.title)
            description = body.get('description', course.description)
            instructor = body.get('instructor', course.instructor)
            topics = body.get('topics', course.topics)
            price = body.get('price', course.price)
            thumbnail_url = body.get('thumbnail_image', course.thumbnail_image)  

            course.title = title
            course.description = description
            course.instructor = instructor
            course.topics = topics
            course.price = price
            course.thumbnail_image = thumbnail_url
            course.save()
            return JsonResponse({
                "status": "success",
                "message": "Course updated",
                "data": {
                    "id": str(course.id),
                    "title": course.title,
                    "description": course.description,
                    "instructor": course.instructor,
                    "topics": course.topics,
                    "price": course.price,
                    "thumbnail_image": course.thumbnail_image,
                    "created_at": course.created_at.isoformat() if hasattr(course, 'created_at') else None,
                    "updated_at": course.updated_at.isoformat() if hasattr(course, 'updated_at') else None
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)
        
    elif request.method == 'DELETE':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
        course.delete()
        return JsonResponse({}, status=204)
    
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)

@csrf_exempt
def api_course_modules(request, course_id):
    user = get_user_from_token(request)
    course = CourseEntry.objects.filter(id=course_id).first()
    if not course:
        return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)

    if request.method == 'GET':
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 15)), 50)
        modules = ModuleEntry.objects.filter(course=course).order_by('order')
        total_items = modules.count()
        total_pages = (total_items + limit - 1) // limit
        modules = modules[(page-1)*limit : page*limit]
        data = []
        for m in modules:
            is_completed = False
            if user:
                is_completed = ModuleProgress.objects.filter(user=user, module=m, is_completed=True).exists()
            data.append({
                "id": str(m.id),
                "course_id": str(course.id),
                "title": m.title,
                "description": m.description,
                "order": m.order,
                "pdf_content": m.pdf_content,      # hanya URL
                "video_content": m.video_content,  # hanya URL
                "is_completed": is_completed,
                "created_at": m.created_at.isoformat() if hasattr(m, 'created_at') else None,
                "updated_at": m.updated_at.isoformat() if hasattr(m, 'updated_at') else None
            })
        return JsonResponse({
            "status": "success",
            "message": "",
            "data": data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_items
            }
        })

    elif request.method == 'POST':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
        try:
            body = json.loads(request.body)
            title = body.get('title')
            description = body.get('description')
            order = int(body.get('order', 1))
            pdf_url = body.get('pdf_content')     
            video_url = body.get('video_content')  

            module = ModuleEntry.objects.create(
                course=course,
                title=title,
                description=description,
                order=order,
                pdf_content=pdf_url,
                video_content=video_url
            )
            return JsonResponse({
                "status": "success",
                "message": "Module created",
                "data": {
                    "id": str(module.id),
                    "course_id": str(course.id),
                    "title": module.title,
                    "description": module.description,
                    "order": module.order,
                    "pdf_content": module.pdf_content,
                    "video_content": module.video_content,
                    "created_at": module.created_at.isoformat() if hasattr(module, 'created_at') else None,
                    "updated_at": module.updated_at.isoformat() if hasattr(module, 'updated_at') else None
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

@csrf_exempt
def api_module_detail(request, module_id):
    user = get_user_from_token(request)
    module = ModuleEntry.objects.filter(id=module_id).first()
    if not module:
        return JsonResponse({'status': 'error', 'message': 'Module not found', 'data': None}, status=404)
    is_completed = False
    if user:
        is_completed = ModuleProgress.objects.filter(user=user, module=module, is_completed=True).exists()

    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "message": "",
            "data": {
                "id": str(module.id),
                "course_id": str(module.course.id),
                "title": module.title,
                "description": module.description,
                "order": module.order,
                "pdf_content": module.pdf_content,
                "video_content": module.video_content,
                "is_completed": is_completed,
                "created_at": module.created_at.isoformat() if hasattr(module, 'created_at') else None,
                "updated_at": module.updated_at.isoformat() if hasattr(module, 'updated_at') else None
            }
        })

    elif request.method == 'PUT':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
        try:
            body = json.loads(request.body)
            title = body.get('title', module.title)
            description = body.get('description', module.description)
            order = int(body.get('order', module.order))
            pdf_url = body.get('pdf_content', module.pdf_content)
            video_url = body.get('video_content', module.video_content)

            module.title = title
            module.description = description
            module.order = order
            module.pdf_content = pdf_url
            module.video_content = video_url
            module.save()
            return JsonResponse({
                "status": "success",
                "message": "Module updated",
                "data": {
                    "id": str(module.id),
                    "course_id": str(module.course.id),
                    "title": module.title,
                    "description": module.description,
                    "order": module.order,
                    "pdf_content": module.pdf_content,
                    "video_content": module.video_content,
                    "created_at": module.created_at.isoformat() if hasattr(module, 'created_at') else None,
                    "updated_at": module.updated_at.isoformat() if hasattr(module, 'updated_at') else None
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    elif request.method == 'DELETE':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
        module.delete()
        return JsonResponse({}, status=204)

@csrf_exempt
def api_module_complete(request, module_id):
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    module = ModuleEntry.objects.filter(id=module_id).first()
    if not module:
        return JsonResponse({'status': 'error', 'message': 'Module not found', 'data': None}, status=404)
    
    progress, _ = ModuleProgress.objects.get_or_create(user=user, module=module)
    progress.is_completed = True
    progress.save()
    total_modules = ModuleEntry.objects.filter(course=module.course).count()
    completed_modules = ModuleProgress.objects.filter(user=user, module__course=module.course, is_completed=True).count()
    percentage = int((completed_modules / total_modules) * 100) if total_modules > 0 else 0
    certificate_url = None
    if percentage == 100:
        certificate_url = f"/api/courses/{module.course.id}/certificate"
    return JsonResponse({
        "status": "success",
        "message": "Module completed",
        "data": {
            "module_id": str(module.id),
            "is_completed": True,
            "course_progress": {
                "total_modules": total_modules,
                "completed_modules": completed_modules,
                "percentage": percentage
            },
            "certificate_url": certificate_url
        }
    })

@csrf_exempt
def api_module_reorder(request, course_id):
    user = get_user_from_token(request)
    if not user or not user.is_administrator:
        return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)
    if request.method != 'PATCH':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)
    try:
        body = json.loads(request.body)
        module_order = body.get('module_order', [])
        result = []
        for item in module_order:
            module = ModuleEntry.objects.filter(id=item['id'], course__id=course_id).first()
            if module:
                module.order = item['order']
                module.save()
                result.append({'id': str(module.id), 'order': module.order})
        return JsonResponse({
            "status": "success",
            "message": "Module order updated",
            "data": {"module_order": result}
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)


@csrf_exempt
def api_buy_course(request, course_id):
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    course = CourseEntry.objects.filter(id=course_id).first()
    if not course:
        return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)
    if CoursePurchase.objects.filter(user=user, course=course).exists():
        return JsonResponse({'status': 'error', 'message': 'Course already purchased', 'data': None}, status=400)
    if user.balance < course.price:
        return JsonResponse({'status': 'error', 'message': 'Balance not enough', 'data': None}, status=400)
    user.balance -= course.price
    user.save()
    purchase = CoursePurchase.objects.create(user=user, course=course)
    return JsonResponse({
        "status": "success",
        "message": "Course purchased",
        "data": {
            "course_id": str(course.id),
            "user_balance": user.balance,
            "transaction_id": str(purchase.id)
        }
    })

@csrf_exempt
def api_my_courses(request):
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    q = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 15)), 50)
    purchases = CoursePurchase.objects.filter(user=user, course__title__icontains=q).order_by('-purchased_at')
    total_items = purchases.count()
    total_pages = (total_items + limit - 1) // limit
    purchases = purchases[(page-1)*limit : page*limit]
    data = []
    for p in purchases:
        course = p.course
        total_modules = course.modules.count()
        completed_modules = ModuleProgress.objects.filter(user=user, module__course=course, is_completed=True).count()
        progress_percentage = int((completed_modules / total_modules) * 100) if total_modules > 0 else 0
        data.append({
            "id": str(course.id),
            "title": course.title,
            "instructor": course.instructor,
            "topics": course.topics,
            "thumbnail_image": course.thumbnail_image,
            "progress_percentage": progress_percentage,
            "purchased_at": p.purchased_at.isoformat()
        })
    return JsonResponse({
        "status": "success",
        "message": "",
        "data": data,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items
        }
    })


@csrf_exempt
def api_users(request):
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    if request.method == 'GET':
        q = request.GET.get('q', '')
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 15)), 50)
        users = CustomUser.objects.filter(
            models.Q(username__icontains=q) |
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q) |
            models.Q(email__icontains=q)
        ).order_by('-id')
        total_items = users.count()
        total_pages = (total_items + limit - 1) // limit
        users = users[(page-1)*limit : page*limit]
        data = []
        for u in users:
            data.append({
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "balance": u.balance
            })
        return JsonResponse({
            "status": "success",
            "message": "",
            "data": data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_items
            }
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)

@csrf_exempt
def api_user_detail(request, user_id):
    user = get_user_from_token(request)
    target = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    if not target:
        return JsonResponse({'status': 'error', 'message': 'User not found', 'data': None}, status=404)
    if request.method == 'GET':
        courses_purchased = CoursePurchase.objects.filter(user=target).count()
        return JsonResponse({
            "status": "success",
            "message": "",
            "data": {
                "id": str(target.id),
                "username": target.username,
                "email": target.email,
                "first_name": target.first_name,
                "last_name": target.last_name,
                "balance": target.balance,
                "courses_purchased": courses_purchased
            }
        })
    elif request.method == 'PUT':
        if target.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Cannot update admin', 'data': None}, status=403)
        try:
            body = json.loads(request.body)
            target.email = body.get('email', target.email)
            target.username = body.get('username', target.username)
            target.first_name = body.get('first_name', target.first_name)
            target.last_name = body.get('last_name', target.last_name)
            password = body.get('password')
            if password:
                target.set_password(password)
            target.save()
            return JsonResponse({
                "status": "success",
                "message": "User updated",
                "data": {
                    "id": str(target.id),
                    "username": target.username,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                    "balance": target.balance
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)
    elif request.method == 'DELETE':
        if target.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Cannot delete admin', 'data': None}, status=403)
        target.delete()
        return JsonResponse({}, status=204)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)

@csrf_exempt
def api_user_balance(request, user_id):
    user = get_user_from_token(request)
    target = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)
    if not target:
        return JsonResponse({'status': 'error', 'message': 'User not found', 'data': None}, status=404)
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            increment = int(body.get('increment', 0))
            target.balance += increment
            target.save()
            return JsonResponse({
                "status": "success",
                "message": "Balance updated",
                "data": {
                    "id": str(target.id),
                    "username": target.username,
                    "balance": target.balance
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)
    else:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)

def show_courses(request):
    q = request.GET.get('q', '')
    courses = CourseEntry.objects.all()
    if q:
        courses = courses.filter(
            models.Q(title__icontains=q) |
            models.Q(description__icontains=q) |
            models.Q(instructor__icontains=q)
        )
    return render(request, 'courses.html', {'courses': courses})

def show_xml(request):
    course_entries = CourseEntry.objects.all()
    data = serializers.serialize('xml', course_entries)
    return HttpResponse(data, content_type='application/xml')

def show_json(request):
    course_entries = CourseEntry.objects.all()
    data = serializers.serialize('json', course_entries)
    return HttpResponse(data, content_type='application/json')
