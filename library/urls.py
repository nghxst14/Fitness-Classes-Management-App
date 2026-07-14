from django.urls import path

from . import views

urlpatterns = [
    path("videos/", views.video_list, name="video_list"),
    path("videos/<int:pk>/", views.video_detail, name="video_detail"),
]
