"""
- отдельная заметка передаётся на страницу со списком заметок в списке `object_list` в словаре `context`;
- в список заметок одного пользователя не попадают заметки другого пользователя;
- на страницы создания и редактирования заметки передаются  формы.
"""

from django.shortcuts import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

from notes.models import Note

User = get_user_model()


class TestContent(TestCase):
    NEWS_COUNT = 10

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username='author')
        cls.author_news = [
            Note(title='Заголовок', text='Текст', slug=f'title_{cls.author}_{i}', author=cls.author)
            for i in range(cls.NEWS_COUNT)
        ]
        for item in cls.author_news:
            item.save()
        Note.objects.bulk_create(cls.author_news)

        cls.other_author = User.objects.create_user(username='other_author')
        cls.other_author_news = [
            Note(title='Заголовок', text='Текст', slug=f'title_{cls.other_author}_{i}', author=cls.other_author)
            for i in range(cls.NEWS_COUNT)
        ]
        Note.objects.bulk_create(cls.other_author_news)

    def test_show_only_author_news(self):
        """В список заметок одного пользователя не попадают заметки другого пользователя."""
        url = reverse('notes:list')

        authors_news = (
            (self.author, self.author_news,),
            (self.other_author, self.other_author_news),
        )

        for author, news in authors_news:
            self.client.force_login(author)
            with self.subTest(author=author):
                response = self.client.get(url)
                object_list = response.context['object_list']
                self.assertQuerysetEqual(
                    object_list, news, ordered=False
                )

    def test_content_in_context(self):
        """Отдельная заметка передаётся на страницу со списком заметок в списке `object_list` в словаре `context`.
        На страницы создания и редактирования заметки передаются формы."""
        news_slug = self.author_news[0].slug
        urls = (
            ('notes:list', None, 'object_list'),
            ('notes:add', None, 'form'),
            ('notes:edit', (news_slug,), 'form'),
        )
        self.client.force_login(self.author)

        for name, args, content_key in urls:
            with self.subTest(name=name):
                url = reverse(name, args=args)

                response = self.client.get(url)
                self.assertIn(content_key, response.context)
