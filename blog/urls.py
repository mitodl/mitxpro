"""Blog url routes"""
from django.urls import path

from blog.views import BlogView

urlpatterns = [
    path("blog/", BlogView.as_view(), name="blog-view"),
]
