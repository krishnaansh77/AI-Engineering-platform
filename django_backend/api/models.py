import uuid

from django.db import models
from django.utils import timezone


class User(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.EmailField(max_length=320)
    password_hash = models.CharField(max_length=256)
    role = models.CharField(max_length=30)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "users"


class WorkspaceMember(models.Model):
    id = models.UUIDField(primary_key=True)
    workspace_id = models.UUIDField()
    user_id = models.UUIDField()
    role = models.CharField(max_length=30)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "workspace_members"


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "workspaces"


class WorkspaceInvitation(models.Model):
    id = models.UUIDField(primary_key=True)
    workspace_id = models.UUIDField()
    invited_by = models.UUIDField()
    email = models.EmailField(max_length=320)
    role = models.CharField(max_length=30)
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "workspace_invitations"


class Repository(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    github_url = models.URLField(max_length=512)
    description = models.TextField(null=True)
    default_branch = models.CharField(max_length=100, default="main")
    clone_path = models.CharField(max_length=512, null=True)
    languages = models.JSONField(default=list)
    frameworks = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="pending")
    error_message = models.TextField(null=True)
    file_count = models.IntegerField(default=0)
    chunk_count = models.IntegerField(default=0)
    last_indexed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
    owner_id = models.UUIDField(null=True)
    workspace_id = models.UUIDField(null=True)

    class Meta:
        managed = False
        db_table = "repositories"
        ordering = ["-created_at"]


class SourceFile(models.Model):
    id = models.UUIDField(primary_key=True)
    repository_id = models.UUIDField()
    file_path = models.CharField(max_length=1024)
    language = models.CharField(max_length=50)
    size_bytes = models.IntegerField(default=0)
    line_count = models.IntegerField(default=0)
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "source_files"
        ordering = ["file_path"]


class CodeChunk(models.Model):
    id = models.UUIDField(primary_key=True)
    repository_id = models.UUIDField()
    file_id = models.UUIDField()
    file_path = models.CharField(max_length=1024)
    language = models.CharField(max_length=50)
    chunk_type = models.CharField(max_length=20)
    symbol_name = models.CharField(max_length=255, null=True)
    parent_symbol = models.CharField(max_length=255, null=True)
    start_line = models.IntegerField()
    end_line = models.IntegerField()
    content = models.TextField()
    docstring = models.TextField(null=True)
    imports = models.JSONField(default=list)

    class Meta:
        managed = False
        db_table = "code_chunks"
