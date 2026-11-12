from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static

from root import settings
from apps.views import (
    login_view, register_view, posts_view,
    profile_view, logout_view, post_create_view,
    reels_view, follow_list_view, follow_view,
    unfollow_view, media_view, post_detail_view,
    like_view, unlike_view, comment_create_view
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    path('posts/', posts_view, name='post_list'),
    path('posts/<int:post_id>/', post_detail_view, name='post_detail'),
    path('posts/<int:post_id>/like/', like_view, name='like'),
    path('posts/<int:post_id>/unlike/', unlike_view, name='unlike'),
    path('posts/<int:post_id>/comment/', comment_create_view, name='comment_create'),
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