import uuid
from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model — every other model in the project will inherit from this.
    Provides UUID primary key, timestamps, and soft-delete support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True