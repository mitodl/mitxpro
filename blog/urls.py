"""Blog url routes"""
from django.urls import path

from blog.views import BlogListView

urlpatterns = [
    path("api/blog/list/", BlogListView.as_view(), name="blog-list-api"),
]
