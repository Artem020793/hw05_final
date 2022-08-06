from faker import Faker
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.conf import settings

from ..models import Group, Post

fake = Faker()
User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake,
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = Post.objects.get(pk=1)
        group = PostModelTest.group
        field_str = {
            str(post): post.text[:settings.COUNT_WORD],
            str(group): group.title,
        }
        for field, expected_value in field_str.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_value)
