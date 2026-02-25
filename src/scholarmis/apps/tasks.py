from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from scholarmis.framework.files.storage import TenantStorage


@shared_task(name="tasks.cleanup_exports_folder")
def cleanup_exports_folder():
    folder_path = "exports"  # Relative to MEDIA_ROOT
    
    default_storage = TenantStorage()
    
    # Check if folder exists in storage
    if not default_storage.exists(folder_path):
        return f"Directory '{folder_path}' not found in storage."

    # Calculate the 24-hour cutoff using Django's timezone
    cutoff = timezone.now() - timedelta(hours=24)
    
    # listdir returns ([directories], [files])
    _, files = default_storage.listdir(folder_path)
    
    deleted_count = 0
    
    for filename in files:
        file_full_path = f"{folder_path}/{filename}"
        
        # get_modified_time returns a timezone-aware datetime
        mtime = default_storage.get_modified_time(file_full_path)
        
        if mtime < cutoff:
            try:
                default_storage.delete(file_full_path)
                deleted_count += 1
            except Exception as e:
                # In production, use logger.error() instead of print
                print(f"Failed to delete {file_full_path}: {e}")

    return f"Cleanup complete. Deleted {deleted_count} files."