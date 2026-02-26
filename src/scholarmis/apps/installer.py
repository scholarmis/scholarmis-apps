import json
import os
import yaml
from pathlib import Path
from abc import ABC, abstractmethod
from django.apps import apps, AppConfig
from django.db.models import Model
from django.core.management import call_command
from django.templatetags.static import static
from django.db import models
from django.utils.text import slugify
from scholarmis.framework.logging import log_error
from scholarmis.framework.urls import get_valid_url



class BaseLoader(ABC):
    """
    Abstract base class for loading and applying configurations such as options or permissions.
    """

    def __init__(self, app_config: AppConfig, config_dir="config", file_name="", ignore_errors=True):
        self.app_config = app_config
        self.app_path = Path(app_config.path)
        self.app_name = app_config.name
        self.app_label = app_config.label
        self.verbose_name = app_config.verbose_name

        self.config_dir = Path(config_dir)
        self.file_name = file_name
        self.ignore_errors = ignore_errors

    def get_file_path(self) -> Path:
        """Get the absolute full path of the target file."""
        return Path(self.app_path / self.config_dir / self.file_name)

    def _read_json_file(self, file_path: Path):
        """
        Read and parse a JSON file.
        Returns parsed data or False if errors are ignored.
        """
        if not file_path.exists():
            return False if self.ignore_errors else self._raise_file_not_found(file_path)

        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return False if self.ignore_errors else self._raise_json_decode_error(file_path, e)

    def _raise_file_not_found(self, file_path: Path):
        raise FileNotFoundError(f"{file_path} not found.")

    def _raise_json_decode_error(self, file_path: Path, error):
        raise ValueError(f"Error decoding JSON in {file_path}: {error}")

    @abstractmethod
    def load(self):
        """Abstract method to load configurations, must be implemented by subclasses."""
        pass


class Options(BaseLoader):
    """Handles loading and applying options for an app."""

    def __init__(self, app_config:AppConfig, config_dir="config", file_name="options.json", ignore_errors=True):
        super().__init__(app_config, config_dir, file_name, ignore_errors)

    def _validate_options(self, options) -> bool:
        return isinstance(options, dict)

    def _load_options(self, options: dict):
        PREFERRED_LOOKUPS = ("name", "code")
        model_fields_cache = {}

        for model_name, records in options.items():
            model = self.app_config.get_model(model_name)

            if model_name not in model_fields_cache:
                model_fields_cache[model_name] = {
                    f.name for f in model._meta.get_fields() if isinstance(f, models.Field)
                }

            model_fields = model_fields_cache[model_name]

            for record in records:
                filtered_data = {k: v for k, v in record.items() if k in model_fields}

                if "slug" in model_fields and "name" in record:
                    filtered_data["slug"] = slugify(record["name"], allow_unicode=True).replace("-", "_")

                lookup_data = next(
                    ({field: filtered_data[field]} for field in PREFERRED_LOOKUPS if field in filtered_data and filtered_data[field] is not None),
                    None
                )
                if not lookup_data:
                    continue

                defaults_data = {k: v for k, v in filtered_data.items() if k not in lookup_data}
                model.objects.update_or_create(**lookup_data, defaults=defaults_data)

    def load(self):
        options = self._read_json_file(self.get_file_path())
        if options and self._validate_options(options):
            self._load_options(options)


class Settings(BaseLoader):
    """Handles loading and applying settings for an app."""

    def __init__(self, app_config, config_dir="config", file_name="settings.json", ignore_errors=True):
        super().__init__(app_config, config_dir, file_name, ignore_errors)

    def _validate_settings(self, settings) -> bool:
        return isinstance(settings, list)
    
    def _get_data_model(self) -> Model:
        """Retrieve the existing app instance from the database."""
        return apps.get_model("settings", "AppSetting")

    def _load_settings(self, settings: list):
        model = self._get_data_model()

        for setting in settings:
            model.objects.update_or_create(
                app=self.app_name,
                name=setting["name"],
                defaults={
                    "label": setting.get("label"),
                    "value": setting.get("value"),
                    "default": setting.get("default"),
                    "type": setting.get("type", "string"),
                    "options": setting.get("options", {}),
                },
            )

    def load(self):
        settings = self._read_json_file(self.get_file_path())
        if settings and self._validate_settings(settings):
            self._load_settings(settings)


class Permissions(BaseLoader):
    """Handles loading and applying permissions for an app."""

    def __init__(self, app_config, config_dir="config", file_name="permissions.json", ignore_errors=True):
        super().__init__(app_config, config_dir, file_name, ignore_errors)

    def _create_content_type(self):
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get_or_create(
            app_label=self.app_label,
            model=self.verbose_name,
        )[0]

    def _validate_permissions(self, permissions) -> bool:
        return isinstance(permissions, list) and all(
            isinstance(perm, dict) and "codename" in perm and "name" in perm for perm in permissions
        )
    
    def _get_data_model(self) -> Model:
        """Retrieve the existing app instance from the database."""
        return apps.get_model("apps", "App")

    def _load_permissions(self, permissions):
        from django.contrib.auth.models import Permission
        content_type = self._create_content_type()
        model = self._get_data_model()

        app  = model.objects.get(name=self.app_name)

        for perm in permissions:
            permission, _ = Permission.objects.get_or_create(
                codename=perm["codename"],
                name=perm["name"],
                content_type=content_type,
            )
            app.permissions.add(permission)

    def load(self):
        permissions = self._read_json_file(self.get_file_path())
        if permissions and self._validate_permissions(permissions):
            self._load_permissions(permissions)


class Fixtures(BaseLoader):
    """Loads fixtures for a Django app, avoiding duplicates."""

    def __init__(self, app_config: AppConfig, config_dir="fixtures", ignore_errors=True):
        super().__init__(app_config, config_dir, ignore_errors=ignore_errors)

    def _load_fixture(self, fixture_file: Path):
        try:
            data = json.loads(fixture_file.read_text(encoding="utf-8"))
            model = data[0]["model"]
            app_label, model_name = model.split(".")
            model = apps.get_model(app_label, model_name)

            if not model.objects.exists():
                call_command("loaddata", str(fixture_file))
        except Exception as e:
            if not self.ignore_errors:
                raise e

    def load(self) -> bool:
        fixture_dir = self.app_path / self.config_dir
        if not fixture_dir.exists():
            return False
        for fixture_file in fixture_dir.glob("*.json"):
            self._load_fixture(fixture_file)
        return True


class PeriodicTasks(BaseLoader):
    """Handles loading and registering periodic Celery tasks."""

    def __init__(self, app_config, config_dir="celery", file_name="tasks.yml", ignore_errors=True):
        super().__init__(app_config, config_dir, file_name, ignore_errors)

    @staticmethod
    def validate_schedule_format(schedule: str):
        from celery.schedules import crontab
        
        parts = schedule.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid schedule format: {schedule}")
        return crontab(*parts)

    def load(self):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule

        file_path = self.get_file_path()
        if not file_path.exists():
            return {}

        tasks = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}

        for name, details in tasks.items():
            try:
                schedule_str = str(details.get("schedule", ""))
                parts = schedule_str.split()
                
                defaults = {"task": details["task"]}

                # Case A: Standard Cron (5 parts)
                if len(parts) == 5:
                    schedule = self.validate_schedule_format(schedule_str)
                    crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                        minute=schedule.minute,
                        hour=schedule.hour,
                        day_of_month=schedule.day_of_month,
                        month_of_year=schedule.month_of_year,
                        day_of_week=schedule.day_of_week,
                    )
                    defaults["crontab"] = crontab_schedule
                    defaults["interval"] = None  # Clear interval if switching types

                # Case B: Interval (1 part, e.g., "3600")
                elif len(parts) == 1 and parts[0].isdigit():
                    interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                        every=int(parts[0]),
                        period=IntervalSchedule.SECONDS,
                    )
                    defaults["interval"] = interval_schedule
                    defaults["crontab"] = None  # Clear crontab if switching types
                
                else:
                    raise ValueError(f"Unknown schedule format: {schedule_str}")

                PeriodicTask.objects.update_or_create(
                    name=name,
                    defaults=defaults,
                )
            except Exception as e:
                if not self.ignore_errors:
                    raise
                print(f"Error processing task '{name}': {e}")
        
        
class AppInstaller:
    """
    Main class to handle the installation and configuration of an application within a Django project.
    """
    default_icon = "img/app.png"

    def __init__(self, app_config: AppConfig, ignore_errors: bool = True) -> None:
        """
        Initialize the AppInstaller instance.

        Args:
            app_config (AppConfig): The Django application configuration object.
            ignore_errors (bool, optional): Whether to ignore errors during installation. Defaults to True.
        """
        self.app_config = app_config
        self.ignore_errors = ignore_errors

        self.app_path = app_config.path
        self.app_name = app_config.name
        self.app_label = app_config.label
        self.verbose_name = app_config.verbose_name        

        self.description = getattr(app_config, "description", self.verbose_name)
        self.is_default = getattr(app_config, "is_default", True)
        self.is_service = getattr(app_config, "is_service", False)
        self.icon = self._get_icon_url(getattr(app_config, "icon", None))
        self.url = self._get_valid_url(getattr(app_config, "url", None))

        self.options_loader = Options(app_config, ignore_errors=ignore_errors)
        self.settings_loader = Settings(app_config)
        self.permissions_loader = Permissions(app_config, ignore_errors=ignore_errors)
        self.fixtures_loader = Fixtures(app_config, ignore_errors=ignore_errors)
        self.tasks_loader = PeriodicTasks(app_config, ignore_errors=ignore_errors)


    def _get_icon_url(self, icon: str) -> str:
        """
        Get the URL of the app"s icon, falling back to a default if necessary.

        Args:
            icon (str): The icon filename.

        Returns:
            str: URL to the icon.
        """
        file_path = os.path.join(self.app_label, icon) if icon else self.default_icon
        return static(file_path)
    
    def _get_valid_url(self, url: str) -> str:
        """
        Validate and return a properly formatted URL.

        Args:
            url (str): The URL string.

        Returns:
            str: Validated URL or None if the URL is invalid.
        """
        return get_valid_url(url) if url else None
    
    def _get_app_model(self):
        """
        Get the App model from the app.

        Returns:
            Model: The App model.
        """
        return apps.get_model("apps", "App")

    def create_app(self):
        """
        Create or get the app instance in the database.

        Returns:
            tuple: The app instance and a boolean indicating if it was created.
        """
        try:
            model = self._get_app_model()

            app, created = model.objects.get_or_create(
                name=self.app_name,
                verbose_name=self.verbose_name,
                label=self.app_label,
                is_default=self.is_default,
                is_service=self.is_service,
                url=self.url,
                icon=self.icon
            )
            return app, created
        except Exception as e:
            log_error(e)
    
    def load_permissions(self):
        """
        Load app permissions from the default JSON file.
        """
        try:
            self.permissions_loader.load()
        except Exception as e:
            log_error(e)

    def load_options(self):
        """
        Load app options from the default JSON file.
        """
        try:
            self.options_loader.load()
        except Exception as e:
            log_error(e)

    def load_settings(self):
        """
        Load app settings from the default JSON file.
        """
        try:
           self.settings_loader.load()
        except Exception as e:
            log_error(e)
        
    def load_fixtures(self):
        try:
           self.fixtures_loader.load()
        except Exception as e:
            log_error(e)

    def load_tasks(self):
        try:
           self.tasks_loader.load()
        except Exception as e:
            log_error(e)

    def install(self):
        """
        Install the app by creating the instance, loading options, and permissions.
        """
        try:
            self.create_app()
            self.load_options()
            self.load_permissions()
            self.load_fixtures()
            self.load_settings()
            self.load_tasks()
        except Exception as e:
            pass
