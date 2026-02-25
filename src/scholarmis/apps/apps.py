from importlib import import_module
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from scholarmis.apps.installer import AppInstaller



class AppsConfig(AppConfig):
    name = "scholarmis.apps"


    def ready(self):
        post_migrate.connect(self.install, sender=self)
        from django.conf import settings
        for app in settings.INSTALLED_APPS:
            try:
                import_module(f"{app}.api.admin")
            except ModuleNotFoundError:
                continue


    def install(self, **kwargs):
        installer = AppInstaller(self)
        installer.load_tasks()