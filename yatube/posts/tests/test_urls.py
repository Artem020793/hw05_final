from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from faker import Faker

from ..models import Group, Post

fake = Faker()
User = get_user_model()


class PostsURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Artem1993')
        cls.user2 = User.objects.create_user(username='ArtemXXXL')
        cls.group = Group.objects.create(
            slug='group-slug',
            description=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(),
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_2 = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_2.force_login(self.user2)

    def test_urls_status_guest(self):
        """Проверка статуса на странице для гостя"""
        templates_status_chek = {
            reverse('posts:index'): 200,
            reverse('posts:group_list', kwargs={'slug':
                                                self.group.slug}):
                                                    HTTPStatus.OK,
            reverse('posts:profile', kwargs={'username':
                                             self.user.username}):
                                                 HTTPStatus.OK,
            reverse('posts:post_detail', kwargs={'post_id':
                                                 self.post.id}):
                                                    HTTPStatus.OK,
        }
        for url, status in templates_status_chek.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status)

    def test_pages_available_authorized_client(self):
        """Авторизированному пользователю доступна страница /create/"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_authorized_client_page_edit(self):
        """Авторизированного пользователя со страницы /edit/
         переадресовывает на страницу просмотра поста"""
        response = self.authorized_client_2.get(reverse('posts:post_edit',
                                                        kwargs={'post_id':
                                                                self.post.id}))
        self.assertRedirects(response, reverse('posts:post_detail',
                                               kwargs={'post_id':
                                                       self.post.id}))

    def test_pages_available_edit_author(self):
        """Автору поста доступна страница /edit/"""
        self.author_client = Client()
        self.author_client.force_login(self.user)
        response = self.author_client.get(reverse('posts:post_edit',
                                                  args=[self.post.id]))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_pages_template(self):
        """Страница edit используют соответствующий шаблон."""
        self.author_client = Client()
        self.author_client.force_login(self.user)
        response = self.author_client.get(reverse('posts:post_edit',
                                                  args=[self.post.id]))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_create_pages_template(self):
        """Страница create используют соответствующий шаблон."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_create_url_authorized(self):
        """Проверка доступа для авторизованного
        пользователя к созданию/редактированию поста"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Публичные URL-адреса используют соответствующий шаблон."""
        url_template = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args=[self.group.slug]): 'posts/group_list.html',
            reverse('posts:profile',
                    args=[self.user]): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=[self.post.id]): 'posts/post_detail.html',
        }
        for url, template in url_template.items():
            with self.subTest(template=template):
                response = self.client.get(url)
                self.assertTemplateUsed(response, template)

    def test_redirects_guest_user_private_page(self):
        """Приватные адреса недоступны для гостевых пользователей
         и работает переадресация на страницу входа."""
        url_posts_edit = reverse('posts:post_edit', args=[self.post.id])
        url_login = reverse('users:login')
        url_create = reverse('posts:post_create')
        url_redirect = {
            url_posts_edit: f'{url_login}?next={url_posts_edit}',
            url_create: f'{url_login}?next={url_create}'
        }
        for url, redirect in url_redirect.items():
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertRedirects(response, redirect)
