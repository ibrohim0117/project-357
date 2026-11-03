from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static

from root import settings
from apps.views import (
    login_view, register_view, posts_view,
    profile_view, logout_view, post_create_view
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    path('posts/', posts_view, name='post_list'),
    path('post-create/', post_create_view, name='post_create'),

    path('profile/', profile_view, name='profile')
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)