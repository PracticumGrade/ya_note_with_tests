"""
- Главная страница доступна анонимному пользователю.
- Аутентифицированному пользователю доступна страница со списком заметок notes/,
    страница успешного добавления заметки done/, страница добавления новой заметки add/.
- Страницы отдельной заметки, удаления и редактирования заметки доступны только автору заметки.
    Если на эти страницы попытается зайти другой пользователь — вернётся ошибка 404.
- При попытке перейти на страницу списка заметок, страницу успешного добавления записи, страницу добавления заметки,
    отдельной заметки, редактирования или удаления заметки анонимный пользователь перенаправляется на страницу логина.
- Страницы регистрации пользователей, входа в учётную запись и выхода из неё доступны всем пользователям.
"""

from http import HTTPStatus

from django.shortcuts import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

from notes.models import Note

User = get_user_model()


class TestRoutes(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username='author')
        cls.news = Note.objects.create(title='Заголовок', text='Текст', author=cls.author)

        cls.reader = User.objects.create_user(username='reader')

    def news_slug_for_args(self) -> tuple:
        """Получение slug для новости, чтобы использовать его в аргументах при разрешение имени url."""
        return self.news.slug,

    def test_availability_pages_for_anonymous_client(self):
        """Главная страница доступна анонимному пользователю.
        Страницы регистрации пользователей, входа в учётную запись и выхода из неё доступны всем пользователям.
        """
        urls = (
            'notes:home',
            'users:login',
            'users:logout',
            'users:signup',
        )
        for name in urls:
            with self.subTest(name=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_availability_pages_for_authentication_client(self):
        """Аутентифицированному пользователю доступна страница со списком заметок notes/,
        страница успешного добавления заметки done/ и страница добавления новой заметки add/.
        """
        urls = (
            'notes:list',
            'notes:success',
            'notes:add',
        )
        self.client.force_login(self.author)
        for name in urls:
            with self.subTest(name=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_availability_for_note_detail_edit_and_delete(self):
        """Страницы отдельной заметки, удаления и редактирования заметки доступны только автору заметки.
        Если на эти страницы попытается зайти другой пользователь — вернётся ошибка 404."""
        urls = (
            'notes:detail',
            'notes:edit',
            'notes:delete',
        )
        users_statuses = (
            (self.author, HTTPStatus.OK),
            (self.reader, HTTPStatus.NOT_FOUND),
        )
        for user, status in users_statuses:
            self.client.force_login(user)
            for name in urls:
                with self.subTest(user=user, name=name, status=status):
                    url = reverse(name, args=self.news_slug_for_args())
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, status)

    def test_redirect_for_anonymous_client(self):
        """При попытке перейти на страницу списка заметок, страницу успешного добавления записи,
        страницу добавления заметки, отдельной заметки, редактирования или удаления
        заметки анонимный пользователь перенаправляется на страницу логина.
        """
        login_url = reverse('users:login')
        urls = (
            ('notes:list', None),
            ('notes:success', None),
            ('notes:add', None),
            ('notes:detail', self.news_slug_for_args()),
            ('notes:edit', self.news_slug_for_args()),
            ('notes:delete', self.news_slug_for_args()),
        )
        for name, args in urls:
            with self.subTest(name=name):
                url = reverse(name, args=args)

                redirect_url = f'{login_url}?next={url}'
                response = self.client.get(url)
                self.assertRedirects(response, redirect_url)
