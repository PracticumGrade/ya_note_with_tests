"""
- Залогиненный пользователь может создать заметку, а анонимный — не может.
- Невозможно создать две заметки с одинаковым slug.
- Если при создании заметки не заполнен slug, то он формируется автоматически, с помощью функции `pytils.translit.slugify`.
- Пользователь может редактировать и удалять свои заметки, но не может редактировать или удалять чужие.
"""
from http import HTTPStatus

from django.shortcuts import reverse
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from notes.models import Note
from notes.forms import WARNING

User = get_user_model()


class TestCreateNote(TestCase):
    NOTE_TITLE = 'Заголовок'
    NOTE_TEXT = 'Текст'
    NOTE_USER_SLUG = 'slug_title'
    NOTE_AUTO_GENERATED_SLUG = 'zagolovok'
    SLUG_MAX_LEN = 100

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username='author')
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.author)

        cls.url = reverse('notes:add')

        cls.form_data = {
            'title': cls.NOTE_TITLE,
            'text': cls.NOTE_TEXT,
        }
        cls.form_data_with_user_slug = {
            **cls.form_data,
            'slug': cls.NOTE_USER_SLUG,
        }

        cls.success_url = reverse('notes:success')

    def test_anonymous_user_cant_create_note(self):
        """Анонимный пользователь не может создать заметку."""
        self.client.post(self.url, data=self.form_data)

        notes_count = Note.objects.count()
        self.assertEqual(notes_count, 0)

    def test_user_can_create_note(self):
        """Залогиненный пользователь может создать заметку."""
        form_data = (
            (self.form_data, self.NOTE_AUTO_GENERATED_SLUG),
            (self.form_data_with_user_slug, self.NOTE_USER_SLUG)
        )

        for data, slug in form_data:
            with self.subTest(data=data):
                response = self.auth_client.post(self.url, data=data)
                self.assertRedirects(response, self.success_url)

                notes_count = Note.objects.count()
                self.assertEqual(notes_count, 1)

                note = Note.objects.get()
                self.assertEqual(note.title, self.NOTE_TITLE)
                self.assertEqual(note.text, self.NOTE_TEXT)
                self.assertEqual(note.author, self.author)
                self.assertEqual(note.slug, slug)
                note.delete()

    def test_cant_create_news_with_duplicate_slug(self):
        """Невозможно создать две заметки с одинаковым slug."""
        Note.objects.create(author=self.author, **self.form_data)

        response = self.auth_client.post(self.url, data=self.form_data)

        errors = self.NOTE_AUTO_GENERATED_SLUG + WARNING
        self.assertFormError(
            response,
            form='form',
            field='slug',
            errors=errors
        )

        notes_count = Note.objects.count()
        self.assertEqual(notes_count, 1)

    def test_generate_slug(self):
        """Если при создании заметки не заполнен slug, то он формируется автоматически,
        с помощью функции `pytils.translit.slugify`."""
        # заголовок, который будет заведомо больше максимально допустимого размера slug
        very_long_title = "w" + "e" * self.SLUG_MAX_LEN
        very_long_slug = very_long_title[:self.SLUG_MAX_LEN]

        slugs = (
            (self.NOTE_TITLE, 'zagolovok'),
            (very_long_title, very_long_slug)
        )
        for title, slug in slugs:
            with self.subTest(title=title):
                self.assertEqual(Note.get_slug_by_title(title), slug)


class TestNoteEditDelete(TestCase):
    NOTE_TEXT = 'Текст'
    NOTE_NEW_TEXT = 'Обновлённый текст'

    @classmethod
    def setUpTestData(cls):
        # Создаём пользователя - автора заметки.
        cls.author = User.objects.create_user(username='Автор заметки')
        # Создаём клиент для пользователя-автора.
        cls.author_client = Client()
        # "Логиним" пользователя в клиенте.
        cls.author_client.force_login(cls.author)
        # Делаем всё то же самое для пользователя-читателя.
        cls.reader = User.objects.create(username='Читатель')
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)

        # Создаём заметку в БД.
        cls.note = Note.objects.create(title='Заголовок', text=cls.NOTE_TEXT, author=cls.author)

        # Формируем данные для POST-запроса по обновлению заметки.
        cls.form_data = {
            'title': cls.note.title,
            'slug': cls.note.slug,
            'text': cls.NOTE_NEW_TEXT
        }

        cls.edit_url = reverse('notes:edit', args=(cls.note.slug,))  # URL для редактирования.
        cls.delete_url = reverse('notes:delete', args=(cls.note.slug,))  # URL для удаления.

        cls.success_url = reverse('notes:success')

    def test_author_can_edit_note(self):
        # Выполняем запрос на редактирование от имени автора комментария.
        response = self.author_client.post(self.edit_url, data=self.form_data)
        # Проверяем, что сработал редирект.
        self.assertRedirects(response, self.success_url)
        # Обновляем объект заметки.
        self.note.refresh_from_db()
        # Проверяем, что текст комментария соответствует обновлённому.
        self.assertEqual(self.note.text, self.NOTE_NEW_TEXT)

    def test_user_cant_edit_note_of_another_user(self):
        # Выполняем запрос на редактирование от имени другого пользователя.
        response = self.reader_client.post(self.edit_url, data=self.form_data)
        # Проверяем, что вернулась 404 ошибка.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # Обновляем объект заметки.
        self.note.refresh_from_db()
        # Проверяем, что текст остался тем же, что и был.
        self.assertEqual(self.note.text, self.NOTE_TEXT)

    def test_author_can_delete_note(self):
        # От имени автора заметки отправляем DELETE-запрос на удаление.
        response = self.author_client.delete(self.delete_url)
        # Проверяем, что сработал редирект.
        self.assertRedirects(response, self.success_url)
        # Считаем количество комментариев в системе.
        comments_count = Note.objects.count()
        # Ожидаем ноль комментариев в системе.
        self.assertEqual(comments_count, 0)

    def test_user_cant_delete_note_of_another_user(self):
        # Выполняем запрос на удаление от пользователя-читателя.
        response = self.reader_client.delete(self.delete_url)
        # Проверяем, что вернулась 404 ошибка.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # Убедимся, что заметки по-прежнему на месте.
        comments_count = Note.objects.count()
        self.assertEqual(comments_count, 1)
