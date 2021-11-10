import base64
import json

from django.conf import settings
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import get_language, gettext
from django.utils.text import slugify

from .models import Page, PageBlock
from .utils import class_from_name
from .blocks import BlockProcessor


class LanguagesInputMixin(object):
    def get_context(self, *args, **kwargs):
        ctx = super().get_context(*args, **kwargs)
        ctx['languages'] = base64.b64encode(json.dumps({
            key: str(value) for key, value in settings.LANGUAGES
        }).encode()).decode()
        return ctx


class MultiLanguageInput(LanguagesInputMixin, forms.TextInput):
    template_name = 'admin/pageblocks/multi_language_input.html'


class PageBlockEditor(LanguagesInputMixin, forms.TextInput):
    template_name = 'admin/pageblocks/block_editor.html'

    def get_context(self, *args, **kwargs):
        ctx = super().get_context(*args, **kwargs)
        ctx['blocks'] = base64.b64encode(json.dumps({
            block_id: {
                'name': str(block_class.name),
                'description': str(block_class.description),
                'fields': block_class.serialize_field_definitions()
            } for block_id, block_class in Page.get_available_blocks()
        }).encode()).decode()
        ctx['translations'] = base64.b64encode(json.dumps({
            'labelBtnAdd': gettext('Add'),
            'labelUnknown': gettext('Unknown'),
            'labelConfirmRemoveBlock': gettext('Are you sure you want to remove this block?'),
            'labelConfirmCopy': gettext('Are you sure you want to do this?  This will overwrite all of the content in this page for this language.'),
            'labelCopyFrom': gettext('Copy from')
        }).encode()).decode()
        return ctx


class PageAdminForm(forms.ModelForm):
    blocks = forms.JSONField(widget=PageBlockEditor, initial=dict({
        key: [] for key, _ in settings.LANGUAGES
    }), required=False)
    slug = forms.SlugField(required=False)

    class Meta:
        model = Page
        fields = ('title', 'slug',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.init_blocks()

    def init_blocks(self):
        languages = [language for language, _ in settings.LANGUAGES]
        self.fields['blocks'].initial = {
            language: BlockProcessor().blocks_to_representation(self.instance.blocks.filter(parent=None, language=language)) for language in languages
        }

    def clean(self):
        data = self.cleaned_data
        if not data.get('slug', None) and data.get('title', {}):
            data['slug'] = self.generate_slug(data['title'].get(get_language(), gettext('Untitled')))
        return data

    def clean_blocks(self):
        """ Validate the data for each block (and recurse if it's a container block) """
        data = self.cleaned_data['blocks']
        if not data:
            return data

        languages = [language for language, _ in settings.LANGUAGES] + list(data.keys())

        return {
            language: BlockProcessor().clean(data[language], language=language) for language in set(languages)
        }

    def generate_slug(self, val):
        slug = slugify(val)
        offset = 0
        qs = Page.objects.all() if not self.instance and not self.instance.pk else Page.objects.exclude(pk=self.instance.pk)

        while qs.filter(slug=slug).count() > 0:
            offset += 1
            slug = '%s_%d' % (slugify(val), offset)

        return slug

    def save(self, commit=True):
        page = super().save(commit=commit)
        if commit:
            self.save_blocks(page)
        return page

    def save_blocks(self, page):
        block_data = self.cleaned_data.get('blocks', {})
        if not block_data:
            block_data = {}

        languages = [language for language, _ in settings.LANGUAGES] + list(block_data.keys())
        processed_blocks = []
        for language in set(languages):
            processed_blocks += BlockProcessor().save(page, block_data.get(language, []),
                                                      language=language)
