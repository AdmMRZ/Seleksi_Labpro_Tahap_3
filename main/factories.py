from typing import Dict, Any, List


class EntityFactory:
    @staticmethod
    def build_user_create(payload: Dict[str, Any]) -> Dict[str, Any]:
        required = ['username', 'email', 'first_name', 'last_name', 'password', 'confirm_password']
        if not all(payload.get(k) for k in required):
            raise ValueError("Missing required user fields (including confirm_password)")

        if payload['password'] != payload['confirm_password']:
            raise ValueError("Password and confirm_password do not match")

        return {
            'username': str(payload['username']).strip(),
            'email': str(payload['email']).strip().lower(),
            'first_name': str(payload['first_name']).strip(),
            'last_name': str(payload['last_name']).strip(),
            'password': payload['password'],
            'balance': int(payload.get('balance', 0)),
            'is_administrator': bool(payload.get('is_administrator', False))
        }

    @staticmethod
    def build_course_create(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not payload.get('title'):
            raise ValueError("Course title is required")
        return {
            'title': str(payload.get('title')).strip(),
            'description': str(payload.get('description', '')).strip(),
            'instructor': str(payload.get('instructor', '')).strip(),
            'topics': payload.get('topics', []) or [],
            'price': int(payload.get('price', 0)),
            'thumbnail_image': payload.get('thumbnail_image') or None
        }

    @staticmethod
    def build_course_update(existing, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': payload.get('title', existing.title),
            'description': payload.get('description', existing.description),
            'instructor': payload.get('instructor', existing.instructor),
            'topics': payload.get('topics', existing.topics),
            'price': int(payload.get('price', existing.price)),
            'thumbnail_image': payload.get('thumbnail_image', existing.thumbnail_image)
        }

    @staticmethod
    def build_module_create(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not payload.get('title'):
            raise ValueError("Module title is required")
        return {
            'title': str(payload.get('title')).strip(),
            'description': str(payload.get('description', '')).strip(),
            'order': int(payload.get('order', 1)),
            'pdf_content': payload.get('pdf_content') or None,
            'video_content': payload.get('video_content') or None
        }

    @staticmethod
    def build_module_update(existing, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': payload.get('title', existing.title),
            'description': payload.get('description', existing.description),
            'order': int(payload.get('order', existing.order)),
            'pdf_content': payload.get('pdf_content', existing.pdf_content),
            'video_content': payload.get('video_content', existing.video_content)
        }