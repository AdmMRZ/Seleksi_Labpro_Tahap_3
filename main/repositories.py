from typing import Tuple, List, Optional, Dict, Any
from django.db import transaction
from django.db.models import Q, QuerySet
from main.models import (
    CourseEntry,
    ModuleEntry,
    CustomUser,
    ModuleProgress,
    CoursePurchase,
)


def _paginate(qs: QuerySet, page: int, limit: int) -> Tuple[List[Any], int]:
    total = qs.count()
    start = max((page - 1) * limit, 0)
    end = start + limit
    return list(qs[start:end]), total


class CourseRepository:
    @staticmethod
    def list(q: str = '', page: int = 1, limit: int = 15) -> Tuple[List[CourseEntry], int]:
        qs = CourseEntry.objects.all()  
        if q:  
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(instructor__icontains=q) |
                Q(topics__icontains=q)
            )
        qs = qs.order_by('-created_at')
        return _paginate(qs, page, limit)

    @staticmethod
    def get(course_id: str) -> Optional[CourseEntry]:
        return CourseEntry.objects.filter(id=course_id).first()

    @staticmethod
    def create(data: Dict[str, Any]) -> CourseEntry:
        return CourseEntry.objects.create(**data)

    @staticmethod
    def update(course: CourseEntry, data: Dict[str, Any]) -> CourseEntry:
        for k, v in data.items():
            setattr(course, k, v)
        course.save()
        return course

    @staticmethod
    def delete(course: CourseEntry) -> None:
        course.delete()


class ModuleRepository:
    @staticmethod
    def list_by_course(course: CourseEntry, page: int = 1, limit: int = 15) -> Tuple[List[ModuleEntry], int]:
        qs = ModuleEntry.objects.filter(course=course).order_by('order', 'created_at')
        return _paginate(qs, page, limit)

    @staticmethod
    def get(module_id: str) -> Optional[ModuleEntry]:
        return ModuleEntry.objects.filter(id=module_id).first()

    @staticmethod
    def create(course: CourseEntry, data: Dict[str, Any]) -> ModuleEntry:
        data['course'] = course
        return ModuleEntry.objects.create(**data)

    @staticmethod
    def update(module: ModuleEntry, data: Dict[str, Any]) -> ModuleEntry:
        for k, v in data.items():
            setattr(module, k, v)
        module.save()
        return module

    @staticmethod
    def delete(module: ModuleEntry) -> None:
        module.delete()

    @staticmethod
    @transaction.atomic
    def reorder(course: CourseEntry, module_order: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        module_order: [{'id': '<module_id>', 'order': 1}, ...]
        Returns list of {'id': ..., 'order': ...} that were updated.
        """
        result = []
        for item in module_order:
            mid = item.get('id')
            new_order = item.get('order')
            if mid is None or new_order is None:
                continue
            module = ModuleEntry.objects.filter(id=mid, course=course).first()
            if module:
                module.order = new_order
                module.save()
                result.append({'id': str(module.id), 'order': module.order})
        return result


class UserRepository:
    @staticmethod
    def get_by_id(user_id: str) -> Optional[CustomUser]:
        return CustomUser.objects.filter(id=user_id).first()

    @staticmethod
    def get_by_username_or_email(username_or_email: str) -> Optional[CustomUser]:
        return CustomUser.objects.filter(Q(username=username_or_email) | Q(email=username_or_email)).first()

    @staticmethod
    def create_user(data: Dict[str, Any]) -> CustomUser:
        password = data.pop('password', None)
        user = CustomUser.objects.create(**{k: v for k, v in data.items() if k != 'password'})
        if password:
            user.set_password(password)
            user.save()
        return user

    @staticmethod
    def update(user: CustomUser, data: Dict[str, Any]) -> CustomUser:
        password = data.pop('password', None)
        for k, v in data.items():
            setattr(user, k, v)
        if password:
            user.set_password(password)
        user.save()
        return user

    @staticmethod
    def delete(user: CustomUser) -> None:
        user.delete()

    @staticmethod
    def list(q: str = '', page: int = 1, limit: int = 15) -> Tuple[List[CustomUser], int]:
        qs = CustomUser.objects.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        ).order_by('-date_joined')
        return _paginate(qs, page, limit)

    @staticmethod
    def change_balance(user: CustomUser, delta: int) -> CustomUser:
        user.balance = int(user.balance or 0) + int(delta)
        user.save()
        return user


class PurchaseRepository:
    @staticmethod
    def exists(user: CustomUser, course: CourseEntry) -> bool:
        return CoursePurchase.objects.filter(user=user, course=course).exists()

    @staticmethod
    def create(user: CustomUser, course: CourseEntry) -> CoursePurchase:
        return CoursePurchase.objects.create(user=user, course=course)

    @staticmethod
    def list_user_purchases(user: CustomUser, q: str = '', page: int = 1, limit: int = 15) -> Tuple[List[CoursePurchase], int]:
        qs = CoursePurchase.objects.filter(user=user, course__title__icontains=q).order_by('-purchased_at')
        return _paginate(qs, page, limit)


class ProgressRepository:
    @staticmethod
    def get_or_create(user: CustomUser, module: ModuleEntry) -> ModuleProgress:
        progress, _ = ModuleProgress.objects.get_or_create(user=user, module=module)
        return progress

    @staticmethod
    def mark_completed(user: CustomUser, module: ModuleEntry) -> ModuleProgress:
        progress = ProgressRepository.get_or_create(user, module)
        progress.is_completed = True
        progress.save()
        return progress

    @staticmethod
    def total_modules(course: CourseEntry) -> int:
        return ModuleEntry.objects.filter(course=course).count()

    @staticmethod
    def completed_modules_count(user: CustomUser, course: CourseEntry) -> int:
        return ModuleProgress.objects.filter(user=user, module__course=course, is_completed=True).count()