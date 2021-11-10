from django.http.response import Http404
from django.views.generic.base import TemplateView
from django.utils.translation import gettext


class PageView(TemplateView):
    template_name = None
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            raise Exception(gettext('No queryset provided.  This view must provide either a queryset attribute or get_queryset function'))
        return self.queryset

    def get_object(self, *args, **kwargs):
        slug = self.kwargs.get('slug', None)
        if not slug:
            raise Exception(gettext('Expecting a slug parameter on the url.  You can override this behaviour by overriding the get_object function'))
        
        obj = self.get_queryset().filter(slug=slug).first()
        if not obj:
            raise Http404()

        return obj

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['page'] = self.get_object()
        return ctx