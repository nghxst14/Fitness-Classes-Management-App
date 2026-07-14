from django.contrib import admin

from .models import Video, VideoCategory


@admin.register(VideoCategory)
class VideoCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    search_fields = ("name",)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "provider",
        "members_only",
        "published",
        "order",
    )
    list_filter = ("provider", "published", "members_only", "category")
    search_fields = ("title", "description")
    list_editable = ("published", "order")
    autocomplete_fields = ("category",)
