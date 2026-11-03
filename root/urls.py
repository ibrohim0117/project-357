from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static

from root import settings
from apps.views import (
    login_view, register_view, posts_view,
    profile_view, logout_view, post_create_view,
    reels_view, follow_list_view, follow_view,
    unfollow_view, media_view
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    path('posts/', posts_view, name='post_list'),
    path('post-create/', post_create_view, name='post_create'),
    path('reels/', reels_view, name='reels'),

    path('profile/', profile_view, name='profile'),
    path('profile/<int:user_id>/', profile_view, name='user_profile'),
    path('profile/<int:user_id>/followers/', follow_list_view, {'relation': 'followers'}, name='followers'),
    path('profile/<int:user_id>/following/', follow_list_view, {'relation': 'following'}, name='following'),

    path('follow/<int:user_id>/', follow_view, name='follow'),
    path('unfollow/<int:user_id>/', unfollow_view, name='unfollow'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, view=media_view, document_root=settings.MEDIA_ROOT)