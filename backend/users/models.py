from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.conf import settings
from profanity import profanity

class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email,name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email,name, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email


class Book(models.Model):
    isbn = models.CharField(max_length=14, unique=True)
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=255)
    image_link = models.URLField(max_length=200, blank=True)
    buy_link = models.URLField(max_length=200, blank=True)
    users = models.ManyToManyField(CustomUser, related_name='liked_books')
    # Comma seperated field
    genres = models.CharField(max_length=255)

    def __str__(self):
        return self.title