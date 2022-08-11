from faker import Faker

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.conf import settings

from ..models import Group, Post

fake = Faker()
User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug=fake.slug(),
            description=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text=fake.text(),
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        field_str = {
            str(self.post): self.post.text[:settings.COUNT_WORD],
            str(self.group): self.group.title,
        }
        for field, expected_value in field_str.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_value)
