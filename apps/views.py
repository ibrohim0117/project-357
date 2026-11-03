import re

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.static import serve

from .models import Follow, Post, PostMedia, User


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
    tab = 'following' if request.GET.get('tab') == 'following' else 'all'
    post_list = (
        Post.objects.filter(is_archived=False)
        .select_related('author')
        .prefetch_related('media')
        .annotate(like_count=Count('likes'))
    )
    if tab == 'following':
        post_list = post_list.filter(author__in=request.user.following.all())
    return render(request, 'posts.html', context={'post_list': post_list, 'tab': tab})


@login_required(login_url='login')
def reels_view(request):
    reel_list = (
        Post.objects.filter(post_type=Post.PostType.REELS, is_archived=False)
        .select_related('author')
        .prefetch_related('media')
        .annotate(like_count=Count('likes'))
    )
    return render(request, 'reels.html', context={
        'reel_list': reel_list,
        'following_ids': _following_ids(request.user),
    })


@login_required(login_url='login')
def profile_view(request, user_id=None):
    profile_user = request.user if user_id is None else get_object_or_404(User, pk=user_id)
    tab = 'reels' if request.GET.get('tab') == 'reels' else 'posts'
    posts = (
        profile_user.posts.filter(is_archived=False)
        .prefetch_related('media')
        .annotate(like_count=Count('likes'))
    )
    return render(request, 'profile.html', context={
        'profile_user': profile_user,
        'is_own': profile_user == request.user,
        'post_count': posts.count(),
        'posts': posts.filter(post_type=Post.PostType.REELS) if tab == 'reels' else posts,
        'tab': tab,
        'following_ids': _following_ids(request.user),
    })


@login_required(login_url='login')
def follow_list_view(request, user_id, relation):
    profile_user = get_object_or_404(User, pk=user_id)
    return render(request, 'follow-list.html', context={
        'profile_user': profile_user,
        'relation': relation,
        'users': getattr(profile_user, relation).order_by('username'),
        'following_ids': _following_ids(request.user),
    })


@login_required(login_url='login')
@require_POST
def follow_view(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target != request.user:
        Follow.objects.get_or_create(follower=request.user, following=target)
    return _redirect_back(request, user_id)


@login_required(login_url='login')
@require_POST
def unfollow_view(request, user_id):
    Follow.objects.filter(follower=request.user, following_id=user_id).delete()
    return _redirect_back(request, user_id)


def _following_ids(user):
    return set(user.following.values_list('pk', flat=True))


def _redirect_back(request, user_id):
    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return HttpResponseRedirect(next_url)
    return redirect('user_profile', user_id=user_id)


@login_required(login_url='login')
def post_create_view(request):
    if request.method != "POST":
        return render(request, 'post-create.html', {'form_data': {'kind': request.GET.get('kind', 'post')}})

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

    return redirect('reels' if is_reels else 'post_list')


def _read_chunks(file, length):
    with file:
        while length > 0:
            chunk = file.read(min(length, 256 * 1024))
            if not chunk:
                break
            length -= len(chunk)
            yield chunk


# Django'ning serve() Range so'rovini qo'llamaydi, usiz Chrome videoni oldinga-orqaga sura olmaydi
def media_view(request, path, document_root):
    response = serve(request, path, document_root=document_root)
    response['Accept-Ranges'] = 'bytes'

    match = re.fullmatch(r'bytes=(\d*)-(\d*)', request.headers.get('Range', ''))
    if response.status_code != 200 or not match or match.groups() == ('', ''):
        return response

    size = int(response['Content-Length'])
    first, last = match.groups()
    if first:
        start, end = int(first), min(int(last or size - 1), size - 1)
    else:
        start, end = max(size - int(last), 0), size - 1

    file = response.file_to_stream
    if start > end:
        file.close()
        return HttpResponse(status=416, headers={'Content-Range': f'bytes */{size}'})

    file.seek(start)
    length = end - start + 1
    ranged = StreamingHttpResponse(_read_chunks(file, length), status=206, content_type=response['Content-Type'])
    ranged['Content-Length'] = length
    ranged['Content-Range'] = f'bytes {start}-{end}/{size}'
    ranged['Accept-Ranges'] = 'bytes'
    return ranged
