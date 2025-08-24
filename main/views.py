from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from reportlab.pdfgen import canvas
import datetime, jwt, json
from main.services import CourseService, ModuleService, PurchaseService, UserService
from main.factories import EntityFactory

SECRET_KEY = settings.SECRET_KEY

def _unauthorized():
    return JsonResponse({'status': 'error', 'message': 'Unauthorized', 'data': None}, status=401)


def _method_not_allowed():
    return JsonResponse({'status': 'error', 'message': 'Method not allowed', 'data': None}, status=405)


def get_user_from_token(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return UserService.get_user_by_id(payload['id'])
    except Exception:
        return None


@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return _method_not_allowed()
    try:
        body = json.loads(request.body)
        user_data = EntityFactory.build_user_create(body)
        UserService.validate_registration(user_data)
        user = UserService.create_user(user_data)
        return JsonResponse({
            'status': 'success',
            'message': 'Register successful',
            'data': {
                'id': str(user.id),
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    except ValueError as ve:
        return JsonResponse({'status': 'error', 'message': str(ve), 'data': None}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=500)
 

@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return _method_not_allowed()
    try:
        body = json.loads(request.body)
        identifier = body.get('identifier')
        password = body.get('password')
        if not password:
            return JsonResponse({'status': 'error', 'message': 'Missing credentials', 'data': None}, status=400)

        user = UserService.get_user_by_username_or_email(identifier) or UserService.get_user_by_id(identifier)
        if user is None or not user.check_password(password):
            return JsonResponse({'status': 'error', 'message': 'Invalid username/email or password', 'data': None}, status=401)

        payload = {
            'id': str(user.id),
            'username': user.username,
            'is_admin': user.is_administrator,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            'iat': datetime.datetime.utcnow()
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return JsonResponse({'status': 'success', 'message': 'Login successful', 'data': {'username': user.username, 'token': token}})
    except ValueError as ve:
        return JsonResponse({'status': 'error', 'message': str(ve), 'data': None}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=500)


@csrf_exempt
def api_self(request):
    if request.method != 'GET':
        return _method_not_allowed()

    user = get_user_from_token(request)
    if not user:
        return _unauthorized()

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
        courses, total_items = CourseService.list_courses(q=q, page=page, limit=limit)
        total_pages = (total_items + limit - 1) // limit
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
            "pagination": {"current_page": page, "total_pages": total_pages, "total_items": total_items}
        })

    elif request.method == 'POST':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

        try:
            body = json.loads(request.body)
            data = EntityFactory.build_course_create(body)
            course = CourseService.create_course(data)
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
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve), 'data': None}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    else:
        return _method_not_allowed()


@csrf_exempt
def api_course_detail(request, course_id):
    user = get_user_from_token(request)
    course = CourseService.get_course(course_id)

    if not course:
        return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "message": "", "data": {
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
        }})

    elif request.method == 'PUT':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

        try:
            body = json.loads(request.body)
            data = EntityFactory.build_course_update(course, body)
            course = CourseService.update_course(course, data)
            return JsonResponse({"status": "success", "message": "Course updated", "data": {
                "id": str(course.id),
                "title": course.title,
                "description": course.description,
                "instructor": course.instructor,
                "topics": course.topics,
                "price": course.price,
                "thumbnail_image": course.thumbnail_image,
                "created_at": course.created_at.isoformat() if hasattr(course, 'created_at') else None,
                "updated_at": course.updated_at.isoformat() if hasattr(course, 'updated_at') else None
            }})
        
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve), 'data': None}, status=400)
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    elif request.method == 'DELETE':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

        CourseService.delete_course(course)

        return JsonResponse({}, status=204)

    else:
        return _method_not_allowed()


@csrf_exempt
def api_course_modules(request, course_id):
    user = get_user_from_token(request)
    course = CourseService.get_course(course_id)

    if not course:
        return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)

    if request.method == 'GET':
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 15)), 50)
        modules, total_items = ModuleService.list_modules(course, page=page, limit=limit)
        total_pages = (total_items + limit - 1) // limit
        data = []

        for m in modules:
            is_completed = ModuleService.get_module_status(user, m)
            data.append({
                "id": str(m.id),
                "course_id": str(course.id),
                "title": m.title,
                "description": m.description,
                "order": m.order,
                "pdf_content": m.pdf_content,
                "video_content": m.video_content,
                "is_completed": is_completed,
                "created_at": m.created_at.isoformat() if hasattr(m, 'created_at') else None,
                "updated_at": m.updated_at.isoformat() if hasattr(m, 'updated_at') else None
            })

        return JsonResponse({"status": "success", "message": "", "data": data, "pagination": {
            "current_page": page, "total_pages": total_pages, "total_items": total_items
        }})

    elif request.method == 'POST':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

        try:
            body = json.loads(request.body)
            mdata = EntityFactory.build_module_create(body)
            module = ModuleService.create_module(course, mdata)
            return JsonResponse({"status": "success", "message": "Module created", "data": {
                "id": str(module.id),
                "course_id": str(course.id),
                "title": module.title,
                "description": module.description,
                "order": module.order,
                "pdf_content": module.pdf_content,
                "video_content": module.video_content,
                "created_at": module.created_at.isoformat() if hasattr(module, 'created_at') else None,
                "updated_at": module.updated_at.isoformat() if hasattr(module, 'updated_at') else None
            }})
        
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve), 'data': None}, status=400)
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    else:
        return _method_not_allowed()


@csrf_exempt
def api_module_detail(request, module_id):
    user = get_user_from_token(request)
    module = ModuleService.get_module(module_id)

    if not module:
        return JsonResponse({'status': 'error', 'message': 'Module not found', 'data': None}, status=404)

    is_completed = ModuleService.get_module_status(user, module)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "message": "", "data": {
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
        }})

    elif request.method == 'PUT':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

        try:
            body = json.loads(request.body)
            data = EntityFactory.build_module_update(module, body)
            module = ModuleService.update_module(module, data)
            return JsonResponse({"status": "success", "message": "Module updated", "data": {
                "id": str(module.id),
                "course_id": str(module.course.id),
                "title": module.title,
                "description": module.description,
                "order": module.order,
                "pdf_content": module.pdf_content,
                "video_content": module.video_content,
                "created_at": module.created_at.isoformat() if hasattr(module, 'created_at') else None,
                "updated_at": module.updated_at.isoformat() if hasattr(module, 'updated_at') else None
            }})
        
        except ValueError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve), 'data': None}, status=400)
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    elif request.method == 'DELETE':
        if not user or not user.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

        ModuleService.delete_module(module)
        return JsonResponse({}, status=204)

    else:
        return _method_not_allowed()


@csrf_exempt
def api_module_complete(request, module_id):
    user = get_user_from_token(request)
    if (request.method != 'PATCH'):
        return _method_not_allowed()
    
    if not user:
        return _unauthorized()

    module = ModuleService.get_module(module_id)
    if not module:
        return JsonResponse({'status': 'error', 'message': 'Module not found', 'data': None}, status=404)

    progress, certificate_url = ModuleService.mark_completed(user, module)
    return JsonResponse({"status": "success", "message": "Module completed", "data": {
        "module_id": str(module.id),
        "is_completed": True,
        "course_progress": progress,
        "certificate_url": certificate_url
    }})


@csrf_exempt
def api_module_reorder(request, course_id):
    user = get_user_from_token(request)

    if not user or not user.is_administrator:
        return JsonResponse({'status': 'error', 'message': 'Admin only', 'data': None}, status=403)

    if request.method != 'PATCH':
        return _method_not_allowed()

    try:
        body = json.loads(request.body)
        module_order = body.get('module_order', [])
        course = CourseService.get_course(course_id)

        if not course:
            return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)

        result = ModuleService.reorder(course, module_order)
        return JsonResponse({"status": "success", "message": "Module order updated", "data": {"module_order": result}})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)
    
@csrf_exempt
def api_buy_course(request, course_id):
    user = get_user_from_token(request)

    if not user:
        return _unauthorized()

    if request.method != 'POST':
        return _method_not_allowed()

    course = CourseService.get_course(course_id)
    if not course:
        return JsonResponse({'status': 'error', 'message': 'Course not found', 'data': None}, status=404)

    try:
        result = PurchaseService.purchase_course(user, course)

        ok = True
        err = None
        purchase = None
        if isinstance(result, tuple):
            ok, err, purchase = result
        else:
            purchase = result

        if not ok:
            return JsonResponse({'status': 'error', 'message': err or 'Purchase failed', 'data': None}, status=400)

        if not purchase:
            return JsonResponse({'status': 'error', 'message': 'Purchase not created', 'data': None}, status=500)

        return JsonResponse({"status": "success", "message": "Course purchased", "data": {
            "course_id": str(course.id),
            "user_balance": getattr(user, 'balance', None),
            "transaction_id": str(getattr(purchase, 'id', ''))
        }})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=500)

@csrf_exempt
def api_my_courses(request):
    user = get_user_from_token(request)

    if not user:
        return _unauthorized()

    q = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 15)), 50)
    purchases, total_items = PurchaseService.list_user_purchases(user, q=q, page=page, limit=limit)
    total_pages = (total_items + limit - 1) // limit
    data = []

    for p in purchases:
        course = p.course
        total_modules = ModuleService.total_modules(course)
        completed_modules = ModuleService.completed_modules_count(user, course)
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

    return JsonResponse({"status": "success", "message": "", "data": data, "pagination": {
        "current_page": page, "total_pages": total_pages, "total_items": total_items
    }})


@csrf_exempt
def api_users(request):
    user = get_user_from_token(request)

    if not user:
        return _unauthorized()

    if request.method != 'GET':
        return _method_not_allowed()

    q = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 15)), 50)
    users, total_items = UserService.list_users(q=q, page=page, limit=limit)
    total_pages = (total_items + limit - 1) // limit
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

    return JsonResponse({"status": "success", "message": "", "data": data, "pagination": {
        "current_page": page, "total_pages": total_pages, "total_items": total_items
    }})


@csrf_exempt
def api_user_detail(request, user_id):
    user = get_user_from_token(request)
    target = UserService.get_user_by_id(user_id)

    if not user:
        return _unauthorized()

    if not target:
        return JsonResponse({'status': 'error', 'message': 'User not found', 'data': None}, status=404)

    if request.method == 'GET':
        courses_purchased = PurchaseService.list_user_purchases(target, page=1, limit=100)[0]
        return JsonResponse({"status": "success", "message": "", "data": {
            "id": str(target.id),
            "username": target.username,
            "email": target.email,
            "first_name": target.first_name,
            "last_name": target.last_name,
            "balance": target.balance,
            "courses_purchased": courses_purchased
        }})

    elif request.method == 'PUT':
        if target.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Cannot update admin', 'data': None}, status=403)

        try:
            body = json.loads(request.body)
            data = {
                'email': body.get('email', target.email),
                'username': body.get('username', target.username),
                'first_name': body.get('first_name', target.first_name),
                'last_name': body.get('last_name', target.last_name)
            }
            password = body.get('password')
            if password:
                data['password'] = password
            target = UserService.update_user(target, data)

            return JsonResponse({"status": "success", "message": "User updated", "data": {
                "id": str(target.id),
                "username": target.username,
                "first_name": target.first_name,
                "last_name": target.last_name,
                "balance": target.balance
            }})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    elif request.method == 'DELETE':
        if target.is_administrator:
            return JsonResponse({'status': 'error', 'message': 'Cannot delete admin', 'data': None}, status=403)

        UserService.update_user(target, {'is_active': False})
        return JsonResponse({}, status=204)

    else:
        return _method_not_allowed()


@csrf_exempt
def api_user_balance(request, user_id):
    user = get_user_from_token(request)
    target = UserService.get_user_by_id(user_id)

    if not user:
        return _unauthorized()

    if not target:
        return JsonResponse({'status': 'error', 'message': 'User not found', 'data': None}, status=404)

    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            increment = int(body.get('increment', 0))
            target = UserService.change_balance(target, increment)

            return JsonResponse({"status": "success", "message": "Balance updated", "data": {
                "id": str(target.id), "username": target.username, "balance": target.balance
            }})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e), 'data': None}, status=400)

    else:
        return _method_not_allowed()
    
def home_page(request):
    search_query = request.GET.get('q', '')  
    page_number = int(request.GET.get('page', 1))  
    limit = int(request.GET.get('limit', 10)) 

    limit = max(1, min(limit, 50))  
    page_number = max(1, page_number) 

    courses, total_items = CourseService.list_courses(q=search_query, page=page_number, limit=limit)

    paginator = Paginator(courses, limit)
    page_obj = paginator.get_page(page_number)

    return render(request, 'courses.html', {
        'courses': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
        'limit': limit,
    })

def register_page(request):
    if request.method == 'GET':
        return render(request, 'register.html')

    elif request.method == 'POST':
        try:
            user_data = {
                'username': request.POST.get('username'),
                'email': request.POST.get('email'),
                'password': request.POST.get('password'),
                'first_name': request.POST.get('first_name', ''),
                'last_name': request.POST.get('last_name', '')
            }

            UserService.validate_registration(user_data)
            user = UserService.create_user(user_data)
            login(request, user)
            return redirect('/')
        except ValueError as ve:
            return render(request, 'register.html', {'error': str(ve)})
        except Exception as e:
            return render(request, 'register.html', {'error': str(e)})

def login_page(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    elif request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = UserService.get_user_by_username_or_email(username)
        if user and user.check_password(password):
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})

def logout_page(request):
    logout(request)
    return redirect('/')

@login_required
def my_courses_page(request):
    user = request.user
    search_query = request.GET.get('q', '') 
    page_number = int(request.GET.get('page', 1)) 
    limit = int(request.GET.get('limit', 10))  

    limit = max(1, min(limit, 50))  
    page_number = max(1, page_number)

    purchases = PurchaseService.list_user_purchases(user, q=search_query, page=page_number, limit=limit)
    purchased_courses = [p.course for p in purchases[0]]

    paginator = Paginator(purchased_courses, limit)
    page_obj = paginator.get_page(page_number)

    return render(request, 'my_courses.html', {
        'purchased_courses': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
        'limit': limit,
    })

@login_required
def profile_page(request):
    user = request.user

    user_data = {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'balance': user.balance,
    }

    return render(request, 'profile.html', {'user_data': user_data})

def course_detail_page(request, course_id):
    user = request.user
    course = CourseService.get_course(course_id)

    already_purchased = PurchaseService.has_purchased(user, course) if user.is_authenticated else False
    certificate_available = CourseService.certificate_accessible(user, course) if already_purchased else False

    if request.method == 'POST':
        success, error, _ = PurchaseService.purchase_course(user, course)
        if not success:
            return render(request, 'course_detail.html', {
                'course': course,
                'already_purchased': already_purchased,
                'certificate_available': certificate_available,
                'error': error
            })

        return render(request, 'course_detail.html', {
            'course': course,
            'already_purchased': True,
            'certificate_available': certificate_available,
            'success': 'Course purchased successfully!'
        })

    return render(request, 'course_detail.html', {
        'course': course,
        'already_purchased': already_purchased,
        'certificate_available': certificate_available
    })

@login_required
def course_modules_page(request, course_id):
    user = request.user
    course = CourseService.get_course(course_id)

    if not course:
        return render(request, '404.html', {'error': 'Course not found'}, status=404)

    modules, total_items = ModuleService.list_modules(course, page=1, limit=100)

    progress_percentage = CourseService.progress_percentage(user, course)
    certificate_available = CourseService.certificate_accessible(user, course)

    return render(request, 'courses_module.html', {
        'course': course,
        'modules': modules,
        'progress_percentage': progress_percentage,
        'certificate_available': certificate_available,
    })

@login_required
def mark_module_complete(request, module_id):
    user = request.user
    module = ModuleService.get_module(module_id)

    if not module:
        return render(request, '404.html', {'error': 'Module not found'}, status=404)

    if request.method == 'POST':
        progress, certificate_url = ModuleService.mark_completed(user, module)
        return redirect('main:course_modules', course_id=module.course.id)

@login_required
def download_certificate(request, course_id):
    user = request.user
    course = CourseService.get_course(course_id)

    if not course:
        return render(request, '404.html', {'error': 'Course not found'}, status=404)
 
    modules, _ = ModuleService.list_modules(course, page=1, limit=100)
    completed_modules = ModuleService.completed_modules_count(user, course)
    if completed_modules != len(modules):
        return render(request, '403.html', {'error': 'Certificate not available'}, status=403)
 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{course.title}_certificate.pdf"'

    p = canvas.Canvas(response)
    p.drawString(100, 750, "Certificate of Completion")
    p.drawString(100, 700, f"Presented to: {user.first_name} {user.last_name}")
    p.drawString(100, 650, f"For completing the course: {course.title}")
    p.drawString(100, 600, f"Instructor: {course.instructor}")
    p.drawString(100, 550, f"Date: {datetime.date.today().strftime('%B %d, %Y')}")
    p.showPage()
    p.save()

    return response