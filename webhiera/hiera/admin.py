from django.contrib import admin

from .models import HieraMergeable, HieraGroup

admin.site.register(HieraMergeable)
admin.site.register(HieraGroup)
