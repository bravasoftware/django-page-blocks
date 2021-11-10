from django.conf import settings
from django.contrib import admin

from .models import Page
from .forms import PageAdminForm


class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
    change_form_template = 'admin/pageblocks/change_form.html'

    def save_model(self, request, obj, form, change):
        obj.save()
        form.save_blocks(obj)


# admin.site.register(Page, PageAdmin)