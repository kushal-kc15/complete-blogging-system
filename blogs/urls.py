from django.urls import path
from . import views

urlpatterns = [
    path("<int:category_id>/", views.Posts_by_category, name="posts_by_category"),
    path("like/<slug:slug>/", views.like_post, name="like_post"),
    path("bookmark/<slug:slug>/", views.bookmark_post, name="bookmark_post"),
    path("comment/edit/<int:comment_id>/",
         views.edit_comment, name="edit_comment"),
    path("comment/delete/<int:comment_id>/",
         views.delete_comment, name="delete_comment"),
    path("my-bookmarks/", views.my_bookmarks, name="my_bookmarks"),
]
