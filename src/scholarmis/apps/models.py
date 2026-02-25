from django.db import models
from django.contrib.auth.models import Permission
from scholarmis.framework.db.models import BaseModel
from scholarmis.framework.urls import safe_reverse


class App(BaseModel):
    name = models.CharField(max_length=100, unique=True, editable=False)
    label = models.CharField(max_length=100, editable=False)
    verbose_name = models.CharField(max_length=100)
    url = models.CharField(max_length=200, editable=False, blank=True, null=True)
    icon = models.CharField(max_length=200, editable=False, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_service = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, null=True, editable=False)
    permissions = models.ManyToManyField(Permission, related_name="apps", editable=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "App"
        verbose_name_plural = "apps"

    def __str__(self):
        if self.is_service or self.is_default:
            return f"{self.verbose_name} (Default)"
        else:
            return f"{self.verbose_name} (Paid)"

    @property    
    def absolute_url(self):
        return self.get_absolute_url()
    
    def activate(self):
        self.is_active = True
        return self
    
    def deactiate(self):
        self.is_active = False
        return self
    
    def set_service(self):
        self.is_service = True
        return self
    
    def unset_service(self):
        self.is_service = False
        return self

    def get_instance(cls, app_name):
        return cls.objects.filter(name=app_name).first()
    
    def get_absolute_url(self):
        return safe_reverse("home", self.label)
    
    @classmethod
    def get_default_apps(cls):
        """Retrieve all default apps."""
        return cls.objects.filter(is_default=True)

    @classmethod
    def get_paid_apps(cls):
        """Retrieve a combination of service and default apps."""
        return cls.objects.filter(is_default=False, is_service=False)
    
