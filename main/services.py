from typing import Tuple, Optional, Dict, Any, List
from django.db import transaction
from main.repositories import (
    CourseRepository,
    ModuleRepository,
    UserRepository,
    PurchaseRepository,
    ProgressRepository,
)
from main.strategies import get_purchase_strategy


class CourseService:
    @staticmethod
    def list_courses(q: str = '', page: int = 1, limit: int = 15) -> Tuple[List[Any], int]:
        return CourseRepository.list(q=q, page=page, limit=limit)

    @staticmethod
    def get_course(course_id: str):
        return CourseRepository.get(course_id)

    @staticmethod
    def create_course(data: Dict[str, Any]):
        return CourseRepository.create(data)

    @staticmethod
    def update_course(course, data: Dict[str, Any]):
        return CourseRepository.update(course, data)

    @staticmethod
    def delete_course(course):
        return CourseRepository.delete(course)


class ModuleService:
    @staticmethod
    def list_modules(course, page: int = 1, limit: int = 15):
        return ModuleRepository.list_by_course(course, page=page, limit=limit)

    @staticmethod
    def get_module(module_id: str):
        return ModuleRepository.get(module_id)

    @staticmethod
    def create_module(course, data: Dict[str, Any]):
        return ModuleRepository.create(course, data)

    @staticmethod
    def update_module(module, data: Dict[str, Any]):
        return ModuleRepository.update(module, data)

    @staticmethod
    def delete_module(module):
        return ModuleRepository.delete(module)

    @staticmethod
    def mark_completed(user, module):
        ProgressRepository.mark_completed(user, module)
        total = ProgressRepository.total_modules(module.course)
        done = ProgressRepository.completed_modules_count(user, module.course)
        percentage = int((done / total) * 100) if total > 0 else 0
        cert = f"/api/courses/{module.course.id}/certificate" if percentage == 100 else None
        return {
            'total_modules': total,
            'completed_modules': done,
            'percentage': percentage
        }, cert

    @staticmethod
    def get_module_status(user, module):
        progress = ProgressRepository.get_or_create(user, module) if user else None
        return bool(progress and getattr(progress, 'is_completed', False))

    @staticmethod
    def reorder(course, module_order: List[Dict[str, Any]]):
        return ModuleRepository.reorder(course, module_order)

    @staticmethod
    def total_modules(course):
        return ModuleRepository.list_by_course(course, page=1, limit=1)[1]  # list_by_course returns (items, total)

    @staticmethod
    def completed_modules_count(user, course):
        return ProgressRepository.completed_modules_count(user, course)


class PurchaseService:
    @staticmethod
    def purchase_course(user, course):
        strategy = get_purchase_strategy(course)
        ok, err = strategy.can_purchase(user, course)
        if not ok:
            return False, err, None
        try:
            purchase = strategy.execute(user, course)
            return True, None, purchase
        except Exception as e:
            return False, str(e), None

    @staticmethod
    def list_user_purchases(user, q: str = '', page: int = 1, limit: int = 15):
        return PurchaseRepository.list_user_purchases(user, q=q, page=page, limit=limit)


class UserService:
    @staticmethod
    def get_user_by_id(uid: str):
        return UserRepository.get_by_id(uid)

    @staticmethod
    def get_user_by_username_or_email(identifier: str):
        return UserRepository.get_by_username_or_email(identifier)

    @staticmethod
    def create_user(data):
        return UserRepository.create_user(data)

    @staticmethod
    def update_user(user, data):
        return UserRepository.update(user, data)

    @staticmethod
    def change_balance(user, delta: int):
        return UserRepository.change_balance(user, delta)

    @staticmethod
    def list_users(q: str = '', page: int = 1, limit: int = 15):
        return UserRepository.list(q=q, page=page, limit=limit)