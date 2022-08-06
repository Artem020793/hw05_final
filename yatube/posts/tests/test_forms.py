import shutil
import tempfile
from faker import Faker

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings

from ..forms import PostForm
from ..models import Group, Post

fake = Faker()
User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.guest_client = Client()
        self.authorized_client.force_login(self.test_user)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user2)

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
        self.assertEqual(form_data['text'], new_post.text)
        self.assertEqual(self.test_user, new_post.author)
        self.assertEqual(self.group, new_post.group)
        self.assertEqual(new_post.image, 'posts/small.gif')

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
            follow=True
        )
        redirect = reverse(
            'posts:post_detail',
            kwargs={'post_id': post.id})
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=self.group.id,
                author=self.test_user
            ).exists()
        )

    def test_create_post_url_redirect_not_author(self):
        """Адрес редактирования поста для авторизованного пользователя,
        не являющегося автором, ведет на редиректную страницу."""
        self.authorized_client.force_login(PostCreateFormTests.user2)
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit', args=[
                    PostCreateFormTests.post.id]), follow=True
        )
        redirect_address = reverse(
            'posts:post_detail', args={PostCreateFormTests.post.id}
        )
        self.assertRedirects(response, redirect_address)
