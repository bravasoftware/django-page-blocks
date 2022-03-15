# django-page-blocks

django-page-blocks is intended to be a lightweight page content engine that can be integrated into an existing application to give site admins a little more control over page building.  It's inspired by the block system in Wagtail CMS but isn't itself intended to be a full CMS, rather an enhanced version of the built in flatpages module.

This documentation is a bit brief at the moment but hopefully the info below can help you get set up.

It was developed and tested on Python 3.9 with Django 3.2.  It will probably work on other recent versions of both as it doesn't do anything particularly special, but your mileage may vary.

The code is still under active development and is very much in an alpha state (hence the lack of documentation.  As always, pull requests and feedback welcome.


## Getting Started

Add the app to your INSTALLED_APPS

```
INSTALLED_APPS = [
  ...
  'pageblocks'
  ...
]
```

You can then either use the base model pageblocks.Page or extend it.


## Admin

To allow proper editing of your pages, django-page-blocks provides an admin base class you can use against either your models, or the default one .. e.g.

```
from pageblocks.admin import PageAdmin

admin.site.register(Page, PageAdmin)
```


## Serving Pages

You can serve pages by extending the PageView class.  Your exact needs may differ, but here's a step by step example to look up and display a page based on it's slug field.

1. Create a view extending the PageView class, defining either a queryset attribute or a get_queryset function to return a queryset of your page records for filtering.  By default the view will select an object based on the slug url parameter if it's provided, but you can change this by overriding the get_object function:

```
from pageblocks.views import PageView
from myapp.models import Page

class MyPageView(PageView):
  template_name = 'page.html'
  queryset = Page.objects.all()
```

2. Create a template (in the above example it should be page.html) that loads the pageblocks template tag:

```
{% load pageblocks %}
```

The current page will be available in the template as the ``page`` object and you can now render your page content with ``{% pageblocks page %}``.

Of course you can mix and match this to meet your needs.  If you need something more low level, you can render an individual list of blocks with the blocks tag .. e.g. ``{% blocks blocks %}``

3. Add it to your urlpatterns:

```
urlpatterns = [
  ...
  path('<slug:slug>/', MyPageView.as_view())
  ...
]
```

## MultiLanguageField

By default, Page.title is a MultiLanguageField, which simply stores a dictionary with values for each language defined in settings.LANGUAGES.  You can render this or any other MultiLanguageField in a template by using the multilang tag, e.g. ``{% multilang page.title %}``


## Custom Blocks

This package comes with a couple of built in blocks, but you'll probably quickly outgrow them and need to add your own.  You can do this by extending the ``pageblocks.blocks.BaseBlock`` class.

This documentation needs fleshing out a bit, but for now, a good place to start would be to look at the source code for HTMLBlock which should hopefully give you an idea of how to extend it.