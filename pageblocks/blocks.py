import base64
import copy
import imghdr
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy, gettext
from django.core.files.base import ContentFile

from .utils import class_from_name
from .models import PageBlock, Image


class BaseField(object):
    input_type = 'text'
    input_classes = []

    def __init__(self, label=None, required=False, additional_classes=None, *args, **kwargs):
        self.label = label
        self.required = required

        if additional_classes:
            self.input_classes.update(additional_classes)

    def serialize_field_definition(self, id):
        return {
            'required': self.required,
            'input_type': self.input_type,
            'label': str(self.label) if self.label else self.id,
            'class': ' '.join(self.input_classes)
        }
        
class CharField(BaseField):
    input_type = 'text'

class TextField(BaseField):
    input_type = 'textarea'

class HTMLField(TextField):
    input_classes = ['html']

class ImageField(BaseField):
    input_type = 'image'

class BlockStreamField(BaseField):
    input_type = 'blockstream'

    def serialize_field_definition(self, id):
        fd = super().serialize_field_definition(id)
        fd['initial'] = []
        return fd


class BlockValidationError(Exception):
    def __init__(self, msg, field_id):
        super().__init__(msg)
        self.field_id = field_id


class BlockRenderingError(Exception):
    pass


class BlockProcessor(object):
    def blocks_to_representation(self, blocks, data=None):
        if not data:
            data = []

        for page_block in blocks.order_by('index'):
            block_class = class_from_name(page_block.type)
            block = block_class(data=page_block.data, instance=page_block)

            data.append({
                'id': str(page_block.id),
                'type': page_block.type,
                'data': block.data_to_representation()
            })
        return data

    def clean(self, data, parent_indexes=[], language=''):
        if not data:
            return data

        if not language:
            raise Exception('No language')

        for index, block_data in enumerate(data):
            block_class = class_from_name(block_data['type'])
            block = block_class(block_data['data'])
            try:
                block_data['data'] = block.clean(parent_indexes=parent_indexes + [index], language=language)
            except BlockValidationError as bve:
                raise ValidationError(f'B:{language}:{self.format_index(parent_indexes, index)}:{bve.field_id}:' + str(bve))

        return data

    def format_index(self, parent_indexes, index):
        indexes = parent_indexes + [index]
        return ','.join([str(i) for i in indexes])

    def save(self, page, data, parent=None, language=None):
        processed_blocks = []
        
        for block_index, block_data in enumerate(data):
            block_class = class_from_name(block_data['type'])
            block = block_class(block_data,
                                instance=PageBlock.objects.get(page=page, id=block_data['id']) if block_data.get('id', None) else None)

            processed_blocks += block.save(page=page,
                                           language=language if not parent else parent.language,
                                           block_index=block_index, parent=parent)

        if not parent:
            cleanup_qs = PageBlock.objects.filter(page=page, language=language).exclude(id__in=[str(rec.id) for rec in processed_blocks])
            cleanup_qs.delete()

        return processed_blocks

    def render(self, blocks):
        return ''.join([block.get_block().render() for block in blocks])



class BaseBlock(object):
    template_name = None
    name = None
    description = None
    fields = ()

    def __init__(self, data=None, instance=None, *args, **kwargs):
        self.data = data
        self.instance = instance

    @classmethod
    def serialize_field_definitions(cls):
        return {
            id: field.serialize_field_definition(id) for id, field in cls.fields
        }

    def data_to_representation(self):
        return self.data

    def data_to_internal_value(self, data):
        return data

    def clean(self, *args, **kwargs):
        """ Validate the block data """
        for field_id, field in self.fields:
            if field.required and not self.data.get(field_id, None):
                raise BlockValidationError(gettext('This field is required'), field_id=field_id)

        return self.data

    def get_instance_for_saving(self, page, language, block_index, parent, *args, **kwargs):
        instance = self.instance if self.instance else PageBlock(page=page, language=language)
        instance.language = language
        instance.type = self.data['type']
        instance.data = self.data_to_internal_value(self.data['data'])
        instance.index = block_index
        instance.parent = parent
        return instance

    def save(self, page, language, block_index, parent, *args, **kwargs):
        self.instance = self.get_instance_for_saving(page, language, block_index, parent, *args, **kwargs)
        self.instance.save()
        return [self.instance]

    def render(self):
        if not self.template_name:
            raise BlockRenderingError(gettext('No template_name defined for') + '.'.join([self.__class__.__module__, self.__class__.__name__]))
        
        return render_to_string(self.template_name, self.get_render_context_data())

    def get_render_context_data(self, *args, **kwargs):
        return {
            'instance': self.instance,
            'block': self.data_to_representation()
        }


class HTMLBlock(BaseBlock):
    """
    Renders the content as raw HTML
    """
    template_name = 'pageblocks/blocks/html.html'
    name = gettext_lazy('HTML')
    description = gettext_lazy('Raw HTML content')
    fields = (
        ('html', HTMLField(label=gettext_lazy('Content'), required=True)),
    )

class ImageBlock(BaseBlock):
    template_name = 'pageblocks/blocks/image.html'
    name = gettext_lazy('Image')
    description = gettext_lazy('A simple image')
    fields = (
        ('image', ImageField(label=gettext_lazy('Image'), required=True)),
        ('alt', CharField(label=gettext_lazy('Alt text'), required=False)),
        ('class', CharField(label=gettext_lazy('Class'), required=False)),
    )

    def data_to_representation(self):
        data = self.data
        if data.get('image_id', None):
            try:
                data['image'] = Image.objects.get(id=data['image_id']).image.url
            except Image.DoesNotExist:
                pass
        return data

    def data_to_internal_value(self, data):
        image = None
        if self.instance and self.instance.data.get('image_id', None):
            image = Image.objects.filter(id=self.instance.data['image_id']).first()

        if not re.search('^\/|^(?i)http', data['image']):
            if not image:
                image = Image()

            if image.image:
                image.image.delete()

            image.image = self.image_to_content_file(data['image'])
            image.save()

        data['image_id'] = str(image.id) if image else None

        del data['image']
        return data

    def image_to_content_file(self, data):
        if 'data:' in data and ';base64,' in data:
            header, data = data.split(';base64,')

        # Try to decode the file. Return validation error if it fails.
        try:
            decoded_file = base64.b64decode(data)
        except Exception:
            raise TypeError('Invalid image data')

        file_name = str(uuid.uuid4())[:12]
        file_extension = self.get_file_extension(file_name, decoded_file)

        return ContentFile(decoded_file, name="%s.%s" % (file_name, file_extension))

    def get_file_extension(self, file_name, decoded_file):
        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension
        return extension


class ContainerBlock(BaseBlock):
    """
    A special block type that contains sub-blocks (useful for defining layouts such as columns)
    """
    template_name = 'pageblocks/blocks/container.html'
    name = gettext_lazy('Container')
    description = gettext_lazy('A container that contains other blocks')
    fields = (
        ('class', CharField(label=gettext_lazy('Class'), required=False)),
        ('blocks', BlockStreamField(label=gettext_lazy('Blocks'), required=True))
    )

    def clean(self, parent_indexes=[], language='', *args, **kwargs):
        data = super().clean(*args, **kwargs)
        BlockProcessor().clean(data['blocks'], parent_indexes=parent_indexes, language=language)
        return data

    def data_to_representation(self):
        data = super().data_to_representation()
        if self.instance:
            data['blocks'] = BlockProcessor().blocks_to_representation(self.instance.children.all())
        return data

    def save(self, page, language, block_index, parent, *args, **kwargs):
        if not self.instance:
            self.instance = PageBlock(page=page, language=language)

        block_data = copy.deepcopy(self.data['data'])
        sub_blocks = BlockProcessor().save(page, block_data.pop('blocks'), parent=self.instance)

        self.instance.language = language
        self.instance.type = self.data['type']
        self.instance.data = block_data
        self.instance.index = block_index
        self.instance.parent = parent
        self.instance.save()

        return [self.instance] + sub_blocks

    def get_render_context_data(self, *args, **kwargs):
        ctx = super().get_render_context_data(*args, **kwargs)
        ctx['blocks'] = self.instance.children.all().order_by('index')
        return ctx

