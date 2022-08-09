import shutil
import tempfile
from faker import Faker

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache

from ..forms import PostForm
from ..models import Group, Post, Comment

fake = Faker()
User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = Group.objects.create(
            title=fake.text(),
            slug='test_slug',
            description=fake.text()
        )
        cls.test_user = User.objects.create_user(username='test_user')
        cls.user2 = User.objects.create_user(username='ArtemXXXL')

        cls.post = Post.objects.create(
            text=fake.text(),
            author=cls.test_user,
            group=cls.group,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.test_user)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user2)
        cache.clear()

    def test_post(self):
        """Тестирование создания Post"""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': fake.text(),
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        new_post = Post.objects.first()
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': new_post.author}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=new_post.text,
                image=new_post.image
            ).exists
        )
        self.assertEqual(form_data['text'], new_post.text)
        self.assertEqual(self.test_user, new_post.author)
        self.assertEqual(self.group, new_post.group)

    def test_not_create_post_no_authorized_client(self):
        """Неавторизованный клиент, не может создать
        пост и переадресовывается на страницу логина"""
        form_data = {
            'text': fake.text(),
            'group': self.group.id,
        }
        post_count = Post.objects.count()
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        login_url = reverse('users:login')
        create_url = reverse('posts:post_create')
        self.assertRedirects(response, f'{login_url}?next={create_url}')
        self.assertEqual(post_count, Post.objects.count())

    def test_post_edit_authorized_user(self):
        """Авторизованный пользователь. Редактирование поста."""
        post = Post.objects.create(
            text=fake.text(),
            author=self.test_user,
            group=self.group,
        )
        form_data = {
            'text': fake.text(),
            'group': self.group.id,
        }
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
        )
        self.assertEqual(Post.objects.count(), posts_count)
        redirect = reverse(
            'posts:post_detail',
            kwargs={'post_id': post.id})
        post.refresh_from_db()
        self.assertRedirects(response, redirect)
        self.assertEqual(post.text,
                         form_data['text'])
        self.assertEqual(post.author,
                         self.test_user)
        self.assertEqual(post.group,
                         self.group)

    def test_create_post_url_redirect_not_author(self):
        """Адрес редактирования поста для авторизованного пользователя,
        не являющегося автором, ведет на редиректную страницу."""
        self.authorized_client.force_login(PostCreateFormTests.user2)
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit', args=(
                    PostCreateFormTests.post.id,)), follow=True
        )
        redirect_address = reverse(
            'posts:post_detail', args=(PostCreateFormTests.post.id,)
        )
        self.assertRedirects(response, redirect_address)


class CommentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='auth',
            email='test@test.ru',
            password='test',
        )
        cls.group = Group.objects.create(
            title=fake.text(),
            slug='first-slug',
            description=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(),
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentsTests.user)
        cache.clear()

    def test_pages_comment_available_authorized_client(self):
        """Авторизированному пользователю доступна страница /comment/."""
        response = self.authorized_client.get(reverse('posts:add_comment',
                                                      args=[self.post.id]))
        self.assertRedirects(response, reverse('posts:post_detail',
                                               args=[self.post.id]))

    def test_redirects_guest_user_private_page(self):
        """Приватные адреса недоступны для гостевых пользователей
        и работает переадресация на страницу входа."""
        url_posts_edit = reverse('posts:post_edit', args=[self.post.id])
        url_login = reverse('users:login')
        url_create = reverse('posts:post_create')
        url_comments = reverse('posts:add_comment', args=[self.post.id])
        url_redirect = {
            url_posts_edit: f'{url_login}?next={url_posts_edit}',
            url_create: f'{url_login}?next={url_create}',
            url_comments: f'{url_login}?next={url_comments}'
        }
        for url, redirect in url_redirect.items():
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertRedirects(response, redirect)

    def test_add_comments(self):
        """Тест добавления Comments если форма Валидная"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': fake.text(),
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        response_post = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIn('comments', response_post.context)
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(text=form_data['text']).exists())
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}))
