import random
import shutil
import tempfile

from faker import Faker

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.conf import settings

from ..forms import PostForm
from posts.models import Group, Post, Follow

fake = Faker()
User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
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

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug':
                                                   self.group.slug}))
        post_obj = response.context['page_obj'][0]
        group_obj = response.context['group']
        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)
        self.assertEqual(post_obj, self.post)
        self.assertEqual(group_obj, self.group)
        self.assertEqual(post_obj.image, self.post.image)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        reverse_page = reverse('posts:post_detail',
                               kwargs={'post_id': self.post.id})
        response = self.client.get(reverse_page)
        post_obj = response.context['user_post']
        self.assertEqual(post_obj, self.post)
        self.assertEqual(post_obj.image, self.post.image)
        self.assertIn('comments', response.context)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        test_post = response.context['page_obj'][0]
        self.assertEqual(test_post, self.post)
        self.assertEqual(test_post.author, self.post.author)
        self.assertEqual(test_post.text, self.post.text)
        self.assertEqual(test_post.group, self.post.group)
        self.assertEqual(test_post.image, self.post.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:profile',
                                           kwargs={'username':
                                                   self.user.username}))
        self.assertIn('page_obj', response.context)
        test_post = response.context['page_obj'][0]
        self.assertEqual(test_post, self.post)
        self.assertEqual(test_post.author, self.post.author)
        self.assertEqual(test_post.text, self.post.text)
        self.assertEqual(test_post.group, self.post.group)
        self.assertEqual(test_post.image, self.post.image)

    def test_create_and_edit_post_page_show_correct_context(self):
        """Шаблон create_post и edit_post
        сформирован с правильным контекстом."""
        self.author_client = Client()
        self.author_client.force_login(self.user)
        context = {
            self.authorized_client: reverse('posts:post_create'),
            self.author_client: reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id})
        }
        for client, revers in context.items():
            with self.subTest(client=client):
                response = client.get(revers)
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context['form'], PostForm)
                if 'is_edit' in response.context:
                    self.assertEqual(response.context["is_edit"], True)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
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

    def test_pagination(self):
        """Тестирование Paginatora."""
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


class CacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='auth',
            email='test@test.ru',
            password=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(),
        )

    def setUp(self):
        cache.clear()

    def test_cache_index(self):
        """Тест кэширования страницы index.html."""
        first_stage = self.client.get(reverse('posts:index'))
        post = CacheTests.post
        post.delete()
        second_stage = self.client.get(reverse('posts:index'))
        self.assertEqual(first_stage.content, second_stage.content)
        cache.clear()
        third_stage = self.client.get(reverse('posts:index'))
        self.assertNotEqual(first_stage.content, third_stage.content)


class FollowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='user')

    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_follower = User.objects.create_user(
            username=fake.user_name(),
            email='follower@mail.ru',
            password=fake.password()
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
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_no_author = Client()
        cache.clear()

    def test_follow(self):
        """Пользователь может подписываться на других пользователей."""
        test_user = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(test_user)
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        self.client_auth_follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_following.username}))
        follow_exist = Follow.objects.filter(user=self.user_follower,
                                             author=self.user_following
                                             ).exists()
        self.assertTrue(follow_exist)

    def test_unfollow(self):
        """Пользователь может отписываться от других пользователей."""
        test_user = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(test_user)
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        self.client_auth_follower.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_following.username}))
        follow_exist = Follow.objects.filter(user=self.user_following,
                                             author=self.user_follower
                                             ).exists()
        self.assertFalse(follow_exist)

    def test_subscription_feed(self):
        """Запись появляется в ленте подписчиков."""
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response = self.client_auth_follower.get(reverse('posts:follow_index'))
        self.assertIn('page_obj', response.context)
        post_text = response.context['page_obj'][0].text
        self.assertEqual(post_text, post_text)

    def test_subscription_feed_not_follow(self):
        """Запись не появляется в ленте тех, кто не подписчик."""
        Follow.objects.create(user=self.user_following,
                              author=self.user_following)
        response = self.client_auth_following.get(
            reverse('posts:follow_index'))
        post_text = response.context['page_obj'][0].text
        self.assertNotContains(response,
                               FollowTests.user)
        self.assertIn('page_obj', response.context)
        self.assertEqual(post_text, post_text)

    def test_not_follow_user_user(self):
        """Пользователь не может подписаться сам на себя."""
        test_user = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(test_user)
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user.username}))
        follow_exist = Follow.objects.filter(user=self.user,
                                             author=self.user).exists()
        self.assertFalse(follow_exist)
