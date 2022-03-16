import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import get_language, gettext_lazy

from .utils import class_from_name
from . import PAGEBLOCKS_DEFAULT_AVAILABLE


class MultiLanguageField(models.JSONField):
    def __init__(self, default=dict, *args, **kwargs):
        super().__init__(default=default, *args, **kwargs)

    def formfield(self, **kwargs):
        from .forms import MultiLanguageInput
        defaults = {'widget': MultiLanguageInput}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class Page(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True, null=False, blank=False)
    title = MultiLanguageField()

    def __str__(self):
        return self.title.get(get_language(), gettext_lazy('Untitled'))

    @classmethod
    def get_available_block_type_classes(cls):
        try:
            return settings.PAGEBLOCKS_AVAILABLE_BLOCKS
        except AttributeError:
            return PAGEBLOCKS_DEFAULT_AVAILABLE

    @classmethod
    def get_available_blocks(cls):
        return [
            (c, class_from_name(c)) for c in cls.get_available_block_type_classes()
        ]

    def get_blocks_for_language(self, language):
        return self.blocks.filter(language=language, parent=None).order_by('index')


class PageBlock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='blocks', db_index=True)
    language = models.CharField(max_length=2, db_index=True)
    index = models.IntegerField(default=-1)
    type = models.TextField()
    data = models.JSONField(default=dict)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True,
                               related_name='children')

    class Meta:
        ordering = ['index']

    def get_block(self):
        return class_from_name(self.type)(data=self.data, instance=self)


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='pageblocks/%Y/%m/%d/')
