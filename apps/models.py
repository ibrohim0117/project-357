from django.db import models
from django.db.models import F, Q
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator


class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatar/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True, unique=True)
    about = models.CharField(max_length=150, blank=True, default='')
    website = models.URLField(blank=True)
    birthday = models.DateField(blank=True, null=True)
    # user.following.all() — men kuzatayotganlar, user.followers.all() — meni kuzatayotganlar
    following = models.ManyToManyField(
        'self', through='Follow', symmetrical=False, related_name='followers', blank=True,
    )

    def __str__(self):
        return self.username


    @property
    def count_follower(self):
        return self.followers.count()

    @property
    def count_following(self):
        return self.following.count()


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_follow'),
            models.CheckConstraint(condition=~Q(follower=F('following')), name='no_self_follow'),
        ]

    def __str__(self):
        return f'{self.follower} -> {self.following}'


class Post(models.Model):
    class PostType(models.TextChoices):
        IMAGE = 'image', 'Rasm'
        VIDEO = 'video', 'Video'
        CAROUSEL = 'carousel', 'Karusel (bir nechta rasm/video)'
        REELS = 'reels', 'Reels'

    MAX_MEDIA = 20

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    post_type = models.CharField(max_length=10, choices=PostType.choices, default=PostType.IMAGE)
    about = models.CharField(max_length=2200, blank=True, default='')  # Instagram caption limiti 2200 belgi
    location = models.CharField(max_length=200, blank=True, default='')
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post #{self.pk} — {self.author}'


class PostMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Rasm'
        VIDEO = 'video', 'Video'

    IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
    VIDEO_EXTENSIONS = ['mp4', 'mov', 'webm']

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(
        upload_to='posts/',
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)],
    )
    media_type = models.CharField(max_length=5, choices=MediaType.choices)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.get_media_type_display()} #{self.order} — post {self.post_id}'

    @classmethod
    def detect_type(cls, filename):
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext in cls.IMAGE_EXTENSIONS:
            return cls.MediaType.IMAGE
        if ext in cls.VIDEO_EXTENSIONS:
            return cls.MediaType.VIDEO
        return None


class Like(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['author', 'post'], name='unique_like'),
        ]

    def __str__(self):
        return f'{self.author} ♥ {self.post_id}'


class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    text = models.CharField(max_length=2200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author}: {self.text[:30]}'


class SavedPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saves')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_saved_post'),
        ]

    def __str__(self):
        return f'{self.user} saved {self.post_id}'
