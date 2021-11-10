import json

from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy, override as translation_override

from .models import Page, PageBlock
from .forms import PageAdminForm

from . import PAGEBLOCKS_DEFAULT_AVAILABLE

class AvailableBlockTestCase(TestCase):
    """
    Test logic to get available block types, with and without overridden settings
    """

    def test_without_settings_override(self):
        self.assertEqual(Page.get_available_block_type_classes(), PAGEBLOCKS_DEFAULT_AVAILABLE)

    @override_settings(PAGEBLOCKS_AVAILABLE_BLOCKS=[
        'pageblocks.blocks.RawHTMLBlock'
    ])
    def test_with_settings_override(self):
        self.assertEqual(Page.get_available_block_type_classes(), [
            'pageblocks.blocks.RawHTMLBlock'
        ])


@override_settings(LANGUAGES=[
    ('es', gettext_lazy('Spanish')),
    ('en', gettext_lazy('English')),
], LANGUAGE_CODE='en')
class PageEditingTestCase(TestCase):
    def test_create_empty_page(self):
        form = PageAdminForm(data={
            'title': {"es":"prueba", "en":"test"}
        })
        self.assertTrue(form.is_valid(), form.errors)
        with translation_override('en'):
            page = form.save()

        self.assertEqual(page.title['en'], 'test')
        self.assertEqual(page.title['es'], 'prueba')
        self.assertTrue(page.slug is not None)
        self.assertEqual(page.slug, 'test')

    def test_create_basic_page(self):
        form = PageAdminForm(data={
            'slug': 'basic_page',
            'title': {"es":"prueba", "en":"test"},
            'blocks': {"es":[{"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>Es una prueba</b>"}},{"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>Es una prueba otra vez</b>"}}],"en":[{"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>This is a test</b>"}}]}
        })
        self.assertTrue(form.is_valid(), form.errors)
        with translation_override('en'):
            page = form.save()

        self.assertEqual(page.slug, 'basic_page')

        self.assertEqual(page.blocks.filter(language='en').count(), 1)
        self.assertEqual(page.blocks.filter(language='es').count(), 2)

        self.assertEqual(page.blocks.filter(language='en')[0].data['html'], '<b>This is a test</b>')
        self.assertEqual(page.blocks.filter(language='en')[0].index, 0)

        self.assertEqual(page.blocks.filter(language='es')[0].data['html'], '<b>Es una prueba</b>')
        self.assertEqual(page.blocks.filter(language='es')[0].index, 0)
        self.assertEqual(page.blocks.filter(language='es')[1].data['html'], '<b>Es una prueba otra vez</b>')
        self.assertEqual(page.blocks.filter(language='es')[1].index, 1)

    # TODO: Test editing a page .. does it load the blocks properly
    def test_editing_basic_page(self):
        PageBlock.objects.all().delete()

        form = PageAdminForm(data={
            'slug': 'basic_page',
            'title': {"es":"prueba", "en":"test"},
            'blocks': {"es":[{"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>Es una prueba</b>"}},{"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>Es una prueba otra vez</b>"}}],"en":[{"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>This is a test</b>"}}]}
        })
        self.assertTrue(form.is_valid(), form.errors)
        with translation_override('en'):
            page = form.save()

        self.assertEqual(PageBlock.objects.all().count(), 3)

        form = PageAdminForm(instance=page)
        block_edit_data = {"es":[
            {"id": str(page.blocks.filter(language="es")[0].id), "type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>Es una prueba</b>"}},
            {"id": str(page.blocks.filter(language="es")[1].id), "type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>Es una prueba otra vez</b>"}}
        ],"en":
        [
            {"id": str(page.blocks.filter(language="en")[0].id), "type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>This is a test</b>"}}
        ]}
        self.assertDictEqual(form.fields['blocks'].initial, block_edit_data)

        block_edit_data['es'][0]['data']['html'] = '<b>He cambiado!</b>'
        del block_edit_data['es'][1]

        block_edit_data['en'].append(
            {"type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>This is a new block</b>"}}
        )

        form = PageAdminForm(instance=page, data={
            'slug': 'basic_page',
            'title': {"es":"prueba", "en":"test"},
            'blocks': block_edit_data
        })
        self.assertTrue(form.is_valid(), form.errors)

        page = form.save()

        self.assertEqual(page.blocks.filter(language='en').count(), 2)
        self.assertEqual(page.blocks.filter(language='es').count(), 1)

        self.assertEqual(page.blocks.filter(language='en')[0].data['html'], '<b>This is a test</b>')
        self.assertEqual(page.blocks.filter(language='en')[0].index, 0)
        self.assertEqual(page.blocks.filter(language='en')[1].data['html'], '<b>This is a new block</b>')
        self.assertEqual(page.blocks.filter(language='en')[1].index, 1)

        self.assertEqual(page.blocks.filter(language='es')[0].data['html'], '<b>He cambiado!</b>')
        self.assertEqual(page.blocks.filter(language='es')[0].index, 0)

    def test_create_page_missing_required_field(self):
        form = PageAdminForm(data={
            'slug': 'basic_page',
            'title': {"es":"prueba", "en":"test"},
            'blocks': {"es":[],"en":[
                {"type":"pageblocks.blocks.HTMLBlock","data":{}}
            ]}
        })
        with translation_override('en'):
            self.assertFalse(form.is_valid(), 'Form validated when it shouldn\'t have')
            self.assertEqual(form.errors['blocks'].as_text(), '* B:en:0:html:This field is required')

    def test_create_page_with_nested_blocks(self):
        """ ContainerBlocks are special block types which allow other blocks to be embedded within them """

        block_edit_data = {"es":[],"en":[
            {
                "type": "pageblocks.blocks.ContainerBlock",
                "data": {
                    "class": "col-12",
                    "blocks": [
                        {
                            "type":"pageblocks.blocks.HTMLBlock","data":{"html":"<b>This is a sub block</b>"}
                        }
                    ]
                }
            }
        ]}
        form = PageAdminForm(data={
            'slug': 'basic_page',
            'title': {"es":"prueba", "en":"test"},
            'blocks': block_edit_data
        })
        self.assertTrue(form.is_valid(), form.errors)
        with translation_override('en'):
            page = form.save()

        self.assertEqual(page.slug, 'basic_page')

        self.assertEqual(page.blocks.filter(language='en').count(), 2)
        self.assertEqual(page.blocks.filter(language='en', parent=None).count(), 1)

        block_edit_data['en'][0]['id'] = str(page.blocks.filter(language='en', parent=None).first().id)
        block_edit_data['en'][0]['data']['blocks'][0]['id'] = str(page.blocks.filter(language='en').exclude(parent=None).first().id)

        form = PageAdminForm(instance=page)
        self.assertDictEqual(form.fields['blocks'].initial, block_edit_data)


    # TODO: Test creating a page with a required block field (or type) missing