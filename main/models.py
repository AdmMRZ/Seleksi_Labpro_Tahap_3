from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class CustomUser(AbstractUser):
    balance = models.IntegerField(default=0)
    is_administrator = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    
class CourseEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.CharField(max_length=150)
    topics = models.JSONField()
    price = models.IntegerField()
    thumbnail_image = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CoursePurchase(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    course = models.ForeignKey('CourseEntry', on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

class ModuleEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(CourseEntry, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField()
    pdf_content = models.URLField(blank=True, null=True)
    video_content = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ModuleProgress(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    module = models.ForeignKey('ModuleEntry', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'module')

