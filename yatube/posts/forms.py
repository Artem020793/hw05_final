from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        labels = {'group': 'Группа',
                  'text': 'Текст поста',
                  'image': 'Картинка'}
        help_texts = {'group': 'Выберите группу',
                      'text': 'Введите текст поста',
                      'image': 'Загрузите картинку'}
        fields = ['text', 'group', 'image']


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
