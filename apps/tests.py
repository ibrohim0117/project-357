import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .models import Comment, Follow, Like, Post, PostMedia, User
from .views import media_view


def video_file(name='clip.mp4'):
    return SimpleUploadedFile(name, b'0123456789', content_type='video/mp4')


class MediaTestCase(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root)
        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)


class FollowTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user('ali', password='x', phone='1')
        self.vali = User.objects.create_user('vali', password='x', phone='2')
        self.client.force_login(self.ali)

    def test_counts_are_numbers_in_the_right_direction(self):
        Follow.objects.create(follower=self.ali, following=self.vali)
        self.assertEqual(self.ali.count_following, 1)
        self.assertEqual(self.ali.count_follower, 0)
        self.assertEqual(self.vali.count_follower, 1)
        self.assertEqual(self.vali.count_following, 0)

    def test_follow_then_unfollow(self):
        self.client.post(reverse('follow', args=[self.vali.id]))
        self.assertTrue(self.ali.following.filter(pk=self.vali.pk).exists())
        self.client.post(reverse('unfollow', args=[self.vali.id]))
        self.assertFalse(self.ali.following.filter(pk=self.vali.pk).exists())

    def test_follow_twice_keeps_one_row(self):
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('follow', args=[self.vali.id])).status_code, 302)
        self.assertEqual(Follow.objects.count(), 1)

    def test_cannot_follow_self(self):
        response = self.client.post(reverse('follow', args=[self.ali.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_requires_post(self):
        self.assertEqual(self.client.get(reverse('follow', args=[self.vali.id])).status_code, 405)
        self.assertEqual(self.client.get(reverse('unfollow', args=[self.vali.id])).status_code, 405)
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_unknown_user_is_404(self):
        self.assertEqual(self.client.post(reverse('follow', args=[9999])).status_code, 404)

    def test_follow_requires_login(self):
        self.client.logout()
        self.client.post(reverse('follow', args=[self.vali.id]))
        self.assertEqual(Follow.objects.count(), 0)

    def test_redirects_back_to_local_next_only(self):
        url = reverse('follow', args=[self.vali.id])
        response = self.client.post(url, {'next': '/reels/#reel-3'})
        self.assertEqual(response['Location'], '/reels/#reel-3')
        response = self.client.post(url, {'next': 'https://evil.example/'})
        self.assertEqual(response['Location'], reverse('user_profile', args=[self.vali.id]))

    def test_other_profile_shows_button_and_counts(self):
        Follow.objects.create(follower=self.vali, following=self.ali)
        response = self.client.get(reverse('user_profile', args=[self.vali.id]))
        self.assertContains(response, reverse('follow', args=[self.vali.id]))
        self.assertContains(response, '<strong>1</strong> following', html=True)

        Follow.objects.create(follower=self.ali, following=self.vali)
        response = self.client.get(reverse('user_profile', args=[self.vali.id]))
        self.assertContains(response, reverse('unfollow', args=[self.vali.id]))

    def test_own_profile_has_no_follow_button(self):
        for url in [reverse('profile'), reverse('user_profile', args=[self.ali.id])]:
            self.assertNotContains(self.client.get(url), 'class="follow-form"')

    def test_unknown_profile_is_404(self):
        self.assertEqual(self.client.get(reverse('user_profile', args=[9999])).status_code, 404)

    def test_follow_lists(self):
        Follow.objects.create(follower=self.vali, following=self.ali)
        followers = self.client.get(reverse('followers', args=[self.ali.id]))
        following = self.client.get(reverse('following', args=[self.ali.id]))
        self.assertEqual(list(followers.context['users']), [self.vali])
        self.assertEqual(list(following.context['users']), [])

    def test_following_feed_only_has_followed_authors(self):
        Post.objects.create(author=self.vali, about='vali post')
        hasan = User.objects.create_user('hasan', password='x', phone='3')
        Post.objects.create(author=hasan, about='hasan post')
        Follow.objects.create(follower=self.ali, following=self.vali)

        all_posts = self.client.get(reverse('post_list')).context['post_list']
        self.assertEqual(len(all_posts), 2)
        following_posts = self.client.get(reverse('post_list'), {'tab': 'following'}).context['post_list']
        self.assertEqual([post.author for post in following_posts], [self.vali])


class LikeTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user('ali', password='x', phone='1')
        self.vali = User.objects.create_user('vali', password='x', phone='2')
        self.post = Post.objects.create(author=self.vali, about='salom')
        self.client.force_login(self.ali)

    def post_json(self, name, post=None):
        return self.client.post(reverse(name, args=[(post or self.post).id]), headers={'Accept': 'application/json'})

    def test_like_then_unlike_returns_json(self):
        response = self.post_json('like')
        self.assertEqual(response.json(), {'liked': True, 'like_count': 1})
        response = self.post_json('unlike')
        self.assertEqual(response.json(), {'liked': False, 'like_count': 0})

    def test_like_twice_keeps_one_row(self):
        self.post_json('like')
        self.assertEqual(self.post_json('like').json(), {'liked': True, 'like_count': 1})
        self.assertEqual(Like.objects.count(), 1)

    def test_like_without_js_redirects_back(self):
        response = self.client.post(reverse('like', args=[self.post.id]), {'next': '/posts/#post-1'})
        self.assertEqual(response['Location'], '/posts/#post-1')
        response = self.client.post(reverse('unlike', args=[self.post.id]), {'next': 'https://evil.example/'})
        self.assertEqual(response['Location'], reverse('post_detail', args=[self.post.id]))

    def test_like_requires_post_and_login(self):
        self.assertEqual(self.client.get(reverse('like', args=[self.post.id])).status_code, 405)
        self.client.logout()
        self.client.post(reverse('like', args=[self.post.id]))
        self.assertEqual(Like.objects.count(), 0)

    def test_archived_or_unknown_post_is_404(self):
        archived = Post.objects.create(author=self.vali, is_archived=True)
        self.assertEqual(self.post_json('like', archived).status_code, 404)
        self.assertEqual(self.client.post(reverse('like', args=[9999])).status_code, 404)

    def test_feed_shows_like_state_and_counts(self):
        Like.objects.create(author=self.vali, post=self.post)
        Comment.objects.create(author=self.vali, post=self.post, text='a')
        Comment.objects.create(author=self.ali, post=self.post, text='b')

        post = self.client.get(reverse('post_list')).context['post_list'][0]
        self.assertEqual((post.like_count, post.comment_count, post.is_liked), (1, 2, False))

        Like.objects.create(author=self.ali, post=self.post)
        response = self.client.get(reverse('post_list'))
        post = response.context['post_list'][0]
        self.assertEqual((post.like_count, post.comment_count, post.is_liked), (2, 2, True))
        self.assertContains(response, 'aria-pressed="true"')
        self.assertContains(response, reverse('unlike', args=[self.post.id]))


class CommentTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user('ali', password='x', phone='1')
        self.post = Post.objects.create(author=self.ali, about='salom')
        self.client.force_login(self.ali)
        self.url = reverse('comment_create', args=[self.post.id])

    def test_comment_json_returns_rendered_comment(self):
        response = self.client.post(self.url, {'text': '  zo‘r  '}, headers={'Accept': 'application/json'})
        data = response.json()
        self.assertEqual(data['comment_count'], 1)
        self.assertIn('zo‘r', data['html'])
        self.assertIn('class="comment-author"', data['html'])
        self.assertEqual(Comment.objects.get().text, 'zo‘r')

    def test_empty_or_too_long_comment_is_rejected(self):
        for text in ['', '   ', 'x' * 2201]:
            with self.subTest(length=len(text)):
                response = self.client.post(self.url, {'text': text}, headers={'Accept': 'application/json'})
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json())
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_without_js_redirects_back(self):
        response = self.client.post(self.url, {'text': 'salom', 'next': f'/posts/#post-{self.post.id}'})
        self.assertEqual(response['Location'], f'/posts/#post-{self.post.id}')
        self.assertEqual(Comment.objects.count(), 1)

    def test_comment_is_escaped(self):
        self.client.post(self.url, {'text': '<script>alert(1)</script>'})
        response = self.client.get(reverse('post_detail', args=[self.post.id]))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_feed_shows_last_two_comments_oldest_first(self):
        for text in ['birinchi', 'ikkinchi', 'uchinchi']:
            Comment.objects.create(author=self.ali, post=self.post, text=text)
        response = self.client.get(reverse('post_list'))
        post = response.context['post_list'][0]
        self.assertEqual([c.text for c in reversed(post.recent_comments)], ['ikkinchi', 'uchinchi'])
        self.assertNotContains(response, 'birinchi')
        self.assertContains(response, '<span data-comment-count>3</span>', html=True)

    def test_detail_page_lists_all_comments(self):
        for text in ['birinchi', 'ikkinchi', 'uchinchi']:
            Comment.objects.create(author=self.ali, post=self.post, text=text)
        response = self.client.get(reverse('post_detail', args=[self.post.id]))
        self.assertEqual([c.text for c in response.context['comments']], ['birinchi', 'ikkinchi', 'uchinchi'])

    def test_archived_post_detail_is_404(self):
        archived = Post.objects.create(author=self.ali, is_archived=True)
        self.assertEqual(self.client.get(reverse('post_detail', args=[archived.id])).status_code, 404)


class ReelsTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.ali = User.objects.create_user('ali', password='x', phone='1')
        self.client.force_login(self.ali)

    def create_reel(self, **kwargs):
        reel = Post.objects.create(author=self.ali, post_type=Post.PostType.REELS, **kwargs)
        PostMedia.objects.create(post=reel, file=video_file(), media_type=PostMedia.MediaType.VIDEO)
        return reel

    def test_upload_reel_redirects_to_reels(self):
        response = self.client.post(reverse('post_create'), {'kind': 'reels', 'about': 'salom', 'media': video_file()})
        self.assertRedirects(response, reverse('reels'))
        reel = Post.objects.get()
        self.assertEqual(reel.post_type, Post.PostType.REELS)
        self.assertEqual(reel.media.get().media_type, PostMedia.MediaType.VIDEO)

    def test_reel_rejects_image_and_multiple_videos(self):
        image = SimpleUploadedFile('a.png', b'x', content_type='image/png')
        for media in [image, [video_file('a.mp4'), video_file('b.mp4')]]:
            response = self.client.post(reverse('post_create'), {'kind': 'reels', 'media': media})
            self.assertContains(response, 'Reels uchun bitta video tanlang.')
        self.assertEqual(Post.objects.count(), 0)

    def test_create_page_preselects_reels(self):
        response = self.client.get(reverse('post_create'), {'kind': 'reels'})
        self.assertContains(response, 'value="reels" checked')

    def test_reels_page_lists_only_active_reels(self):
        reel = self.create_reel(about='kerakli')
        self.create_reel(about='arxivlangan', is_archived=True)
        Post.objects.create(author=self.ali, about='oddiy post')

        response = self.client.get(reverse('reels'))
        self.assertEqual(list(response.context['reel_list']), [reel])
        self.assertContains(response, f'id="reel-{reel.id}"')
        self.assertNotContains(response, 'arxivlangan')

    def test_empty_reels_page(self):
        self.assertContains(self.client.get(reverse('reels')), 'No reels yet')

    def test_reel_without_media_does_not_break_page(self):
        Post.objects.create(author=self.ali, post_type=Post.PostType.REELS)
        self.assertEqual(self.client.get(reverse('reels')).status_code, 200)

    def test_profile_reels_tab_keeps_total_post_count(self):
        reel = self.create_reel()
        Post.objects.create(author=self.ali)
        response = self.client.get(reverse('profile'), {'tab': 'reels'})
        self.assertEqual(list(response.context['posts']), [reel])
        self.assertEqual(response.context['post_count'], 2)
        self.assertContains(response, f'#reel-{reel.id}')


class MediaViewTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        with open(f'{self.media_root}/clip.mp4', 'wb') as file:
            file.write(b'0123456789')

    def get(self, range_header=None):
        headers = {'Range': range_header} if range_header else {}
        request = RequestFactory().get('/media/clip.mp4', headers=headers)
        return media_view(request, 'clip.mp4', self.media_root)

    def body(self, response):
        return b''.join(response.streaming_content)

    def test_without_range_returns_whole_file(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        self.assertEqual(self.body(response), b'0123456789')

    def test_ranges(self):
        cases = [
            ('bytes=0-1', b'01', 'bytes 0-1/10'),
            ('bytes=7-', b'789', 'bytes 7-9/10'),
            ('bytes=-2', b'89', 'bytes 8-9/10'),
            ('bytes=8-100', b'89', 'bytes 8-9/10'),
        ]
        for header, expected, content_range in cases:
            with self.subTest(header):
                response = self.get(header)
                self.assertEqual(response.status_code, 206)
                self.assertEqual(response['Content-Range'], content_range)
                self.assertEqual(int(response['Content-Length']), len(expected))
                self.assertEqual(response['Content-Type'], 'video/mp4')
                self.assertEqual(self.body(response), expected)

    def test_range_past_end_is_416(self):
        response = self.get('bytes=50-')
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response['Content-Range'], 'bytes */10')
