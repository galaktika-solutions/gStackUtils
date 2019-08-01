from django.contrib import admin

from demo import models


@admin.register(models.FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    pass
