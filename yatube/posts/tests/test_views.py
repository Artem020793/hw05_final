import random
import shutil
import tempfile
from faker import Faker

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.conf import settings

from posts.models import Group, Post, Follow

fake = Faker()
User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug='group-slug',
            description=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(),
            group=cls.group,
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):

        self.authorized_client = Client()
        self.guest_client = Client()
        self.authorized_client.force_login(self.user)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:group_list',
                                                 kwargs={'slug':
                                                         self.group.slug}))
        first_object = response.context['page_obj'][0]
        second_object = response.context['group']
        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)
        self.assertEqual(first_object, self.post)
        self.assertEqual(second_object, self.group)
        self.assertEqual(first_object.image, self.post.image)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        reverse_page = reverse('posts:post_detail',
                               kwargs={'post_id': self.post.id})
        response = (self.guest_client.get(reverse_page))
        first_object = response.context['user_post']
        self.assertIn('user_post', response.context)
        self.assertEqual(first_object, self.post)
        self.assertEqual(first_object.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        test_post = response.context['page_obj'][0]
        self.assertEqual(test_post, self.post)
        self.assertEqual(test_post.author, self.post.author)
        self.assertEqual(test_post.text, self.post.text)
        self.assertEqual(test_post.group, self.post.group)
        self.assertEqual(test_post.image, self.post.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:profile',
                                                 kwargs={'username':
                                                         self.user.username}))
        test_post = response.context['page_obj'][0]
        self.assertEqual(test_post, self.post)
        self.assertEqual(test_post.author, self.post.author)
        self.assertEqual(test_post.text, self.post.text)
        self.assertEqual(test_post.group, self.post.group)
        self.assertEqual(test_post.image, self.post.image)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_page_show_correct_context(self):
        """Шаблон edit_post сформирован с правильным контекстом."""
        self.author_client = Client()
        self.author_client.force_login(self.user)
        response = self.author_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        form_field = response.context.get('form').fields.get('text')
        self.assertIsInstance(form_field, forms.fields.CharField)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Artem1993',
                                            email='test@mail.ru',
                                            password='test_pass',)
        cls.group = Group.objects.create(
            title='Заголовок для тестовой группы',
            slug='test_slug2',
            description='Тестовое описание')

        cls.post_test_count = random.randint(settings.POSTS_CHIK + 1,
                                             settings.POSTS_CHIK * 2)
        for i in range(cls.post_test_count):
            Post.objects.bulk_create([
                Post(text=fake,
                     author=cls.user,
                     group=cls.group)
            ])

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pagination(self):
        """Тестирование Paginatora"""
        count_post_one_page = settings.POSTS_CHIK
        all_count = PaginatorViewsTest.post_test_count
        count_post_two_page = all_count - count_post_one_page
        tested_urls_paginations = {
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user})
        }
        for url in tested_urls_paginations:
            with self.subTest(url=url):
                response_one_page = self.client.get(url)
                self.assertEqual(
                    len(response_one_page.context['page_obj']),
                    settings.POSTS_CHIK)
                response_two_page = self.client.get(url + '?page=2')
                self.assertEqual(
                    len(response_two_page.context['page_obj']),
                    count_post_two_page)


class CommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
            id=1,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(CommentsTests.user)

    def test_add_comment(self):
        """Комментировать посты может только авторизованный пользователь"""
        form_comment = {
            'text': 'тестовый комментарий',
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_comment,
            follow=True
        )
        response = self.authorized_client.get(f'/posts/{self.post.id}/')
        self.assertContains(response, 'text')
        self.authorized_client.logout()
        form_comment_guest = {
            'text': 'тестовый комментарий гостя',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_comment_guest,
            follow=True
        )
        response = self.guest_client.get(f'/posts/{self.post.id}/')
        self.assertNotContains(response, form_comment_guest)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='auth',
            email='test@test.ru',
            password=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(),
            id=1,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Noname')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache_index(self):
        """Тест кэширования страницы index.html"""
        first_stage = self.authorized_client.get(reverse('posts:index'))
        post = Post.objects.get(pk=1)
        post.delete()
        second_stage = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(first_stage.content, second_stage.content)
        cache.clear()
        third_stage = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(first_stage.content, third_stage.content)


class FollowTests(TestCase):
    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_follower = User.objects.create_user(
            username='follower',
            email='follower@mail.ru',
            password='test'
        )
        self.user_following = User.objects.create_user(
            username='following',
            email='following@mail.ru',
            password='test'
        )
        self.post = Post.objects.create(
            author=self.user_following,
            text=fake.text()
        )
        self.client_auth_follower.force_login(self.user_follower)
        self.client_auth_following.force_login(self.user_following)

    def test_follow(self):
        """Пользователь может подписываться на других пользователей"""
        self.client_auth_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_following.username}
            )
        )
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unfollow(self):
        """Пользователь может отписываться от других пользователей"""
        self.client_auth_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_following.username}
            )
        )
        self.client_auth_follower.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user_following.username}
            )
        )
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_subscription_feed(self):
        """Запись появляется в ленте подписчиков"""
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response = self.client_auth_follower.get('/follow/')
        self.assertIn('page_obj', response.context)
        post_text = response.context["page_obj"][0].text
        self.assertEqual(post_text, self.post.text)
        response = self.client_auth_following.get('/follow/')
        self.assertNotContains(response,
                               self.post.text)
