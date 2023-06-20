from django.conf import settings
from django.db import models

from pytils.translit import slugify


class Note(models.Model):
    title = models.CharField(
        'Заголовок',
        max_length=100,
        default='Название заметки',
        help_text='Дайте короткое название заметке'
    )
    text = models.TextField(
        'Текст',
        help_text='Добавьте подробностей'
    )
    slug = models.SlugField(
        'Адрес для страницы с заметкой',
        max_length=100,
        unique=True,
        blank=True,
        help_text=('Укажите адрес для страницы заметки. Используйте только '
                   'латиницу, цифры, дефисы и знаки подчёркивания')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_slug_by_title(self.title)
        super().save(*args, **kwargs)

    @classmethod
    def get_slug_by_title(cls, title):
        """Формирование slug для заметки на основе заголовка."""
        max_slug_length = cls._meta.get_field('slug').max_length
        return slugify(title)[:max_slug_length]
