from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        max_length=200,
    )
    slug = models.SlugField(
        unique=True,
    )
    description = models.TextField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return f'{self.title}'


class Post(models.Model):
    RELATED_NAME = 'posts'
    text = models.TextField(
        'Текст поста',
        help_text='Введите текст поста'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name=RELATED_NAME,
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name=RELATED_NAME,
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField(
        verbose_name='Добавить комментарий',
        help_text='Текст комментария',
    )
    created = models.DateTimeField('Дата публикации', auto_now_add=True)

    def __str__(self):
        return self.text
    
class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            )
        ]
