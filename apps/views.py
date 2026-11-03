from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date

from .models import Post, PostMedia, User


def login_view(request):
    if request.user.is_authenticated:
        return redirect('post_list')

    context = {}
    if request.method == "POST":
        data = request.POST
        username = data.get('username', '').strip()
        password = data.get('password', '')
        db_user = User.objects.filter(username=username).first()
        if db_user and db_user.check_password(password):
            login(request, db_user)
            return redirect('post_list')

        context = {'error': "Username yoki parol xato!", 'username': username}
    return render(request, 'login.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('post_list')

    if request.method != "POST":
        return render(request, 'register.html')

    data = request.POST
    form_data = {
        'email': data.get('email', '').strip().lower(),
        'phone': data.get('phone', '').strip(),
        'first_name': data.get('first_name', '').strip(),
        'username': data.get('username', '').strip(),
        'birthday': data.get('birthday', '').strip(),
    }
    password = data.get('password', '')

    errors = {}

    for field, value in {**form_data, 'password': password}.items():
        if not value:
            errors[field] = "Bu maydon to'ldirilishi shart."

    if 'email' not in errors:
        try:
            validate_email(form_data['email'])
        except ValidationError:
            errors['email'] = "Email noto'g'ri formatda."

    birthday = None
    if 'birthday' not in errors:
        try:
            birthday = parse_date(form_data['birthday'])
        except ValueError:
            pass
        if birthday is None:
            errors['birthday'] = "Sana noto'g'ri formatda."

    if 'username' not in errors and User.objects.filter(username__iexact=form_data['username']).exists():
        errors['username'] = "Bu username band."

    if 'email' not in errors and User.objects.filter(email__iexact=form_data['email']).exists():
        errors['email'] = "Bu email bilan ro'yxatdan o'tilgan."

    if 'phone' not in errors and User.objects.filter(phone=form_data['phone']).exists():
        errors['phone'] = "Bu telefon raqam band."

    if 'password' not in errors:
        try:
            validate_password(password)
        except ValidationError as e:
            errors['password'] = " ".join(e.messages)

    if errors:
        return render(request, 'register.html', {
            'errors': errors,
            'form_data': form_data,   # kiritilgan qiymatlar o'chib ketmasin
        })

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                password=password,           # create_user o'zi hash qiladi
                first_name=form_data['first_name'],
                phone=form_data['phone'],
                birthday=birthday,
            )
    except IntegrityError:
        errors['general'] = "Bu ma'lumotlar bilan user allaqachon mavjud."
        return render(request, 'register.html', {'errors': errors, 'form_data': form_data})

    login(request, user)
    return redirect('post_list')


@login_required(login_url='login')
def posts_view(request):
    post_list = (
        Post.objects.filter(is_archived=False)
        .select_related('author')
        .prefetch_related('media')
        .annotate(like_count=Count('likes'))
    )
    return render(request, 'posts.html', context={'post_list': post_list})


@login_required(login_url='login')
def profile_view(request):
    posts = (
        request.user.posts.filter(is_archived=False)
        .prefetch_related('media')
        .annotate(like_count=Count('likes'))
    )
    return render(request, 'profile.html', context={'posts': posts})


@login_required(login_url='login')
def post_create_view(request):
    if request.method != "POST":
        return render(request, 'post-create.html')

    form_data = {
        'about': request.POST.get('about', '').strip(),
        'location': request.POST.get('location', '').strip(),
        'kind': request.POST.get('kind', 'post'),
    }
    is_reels = form_data['kind'] == 'reels'
    files = request.FILES.getlist('media')
    media_types = [PostMedia.detect_type(f.name) for f in files]

    error = None
    if not files:
        error = "Post uchun kamida bitta rasm yoki video tanlang."
    elif None in media_types:
        error = "Faqat JPG, PNG, WEBP rasm yoki MP4, MOV, WEBM video yuklash mumkin."
    elif len(files) > Post.MAX_MEDIA:
        error = f"Bitta postga ko'pi bilan {Post.MAX_MEDIA} ta rasm/video qo'yish mumkin."
    elif is_reels and media_types != [PostMedia.MediaType.VIDEO]:
        error = "Reels uchun bitta video tanlang."

    if error:
        return render(request, 'post-create.html', {'error': error, 'form_data': form_data})

    if is_reels:
        post_type = Post.PostType.REELS
    elif len(files) > 1:
        post_type = Post.PostType.CAROUSEL
    else:
        post_type = Post.PostType(media_types[0])

    with transaction.atomic():
        post = Post.objects.create(
            author=request.user,
            post_type=post_type,
            about=form_data['about'],
            location=form_data['location'],
        )
        for order, (file, media_type) in enumerate(zip(files, media_types)):
            PostMedia.objects.create(post=post, file=file, media_type=media_type, order=order)

    return redirect('post_list')
