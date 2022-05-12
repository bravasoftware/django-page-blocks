from django import template
from django.conf import settings
from django.utils.translation import get_language
from django.utils.safestring import mark_safe

from ..blocks import BlockProcessor

register = template.Library()

@register.simple_tag
def multilang(val):
    return val.get(get_language(), val.get(settings.LANGUAGE_CODE))


@register.simple_tag
def blocks(page_blocks):
    return mark_safe(BlockProcessor().render(page_blocks))

@register.simple_tag
def block_scripts(page_blocks):
    return mark_safe(BlockProcessor().render_script_tags(page_blocks))

@register.simple_tag
def block_stylesheets(page_blocks):
    return mark_safe(BlockProcessor().render_stylesheet_tags(page_blocks))


def get_blocks_for_page(page):
    qs = page.get_blocks_for_language(get_language())
    if qs.count() == 0:
        qs = page.get_blocks_for_language(settings.LANGUAGE_CODE)
    return qs

@register.simple_tag
def pageblocks(page):
    return blocks(get_blocks_for_page(page))

@register.simple_tag
def pageblocks_scripts(page):
    return block_scripts(get_blocks_for_page(page))

@register.simple_tag
def pageblocks_stylesheets(page):
    return block_stylesheets(get_blocks_for_page(page))
