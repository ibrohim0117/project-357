from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Comment, Follow, Like, Post, PostMedia, SavedPost, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Instagram', {'fields': ('avatar', 'phone', 'about', 'website', 'birthday')}),
    )
    list_display = ['username', 'phone', 'first_name', 'count_follower', 'count_following', 'id']


class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 1


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'post_type', 'created_at', 'is_archived']
    list_filter = ['post_type', 'is_archived']
    inlines = [PostMediaInline]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'id', 'created_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'parent', 'text', 'created_at']
    search_fields = ['text']


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at']


@admin.register(SavedPost)
class SavePostAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
