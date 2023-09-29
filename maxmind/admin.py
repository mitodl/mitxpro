"""Admin for maxmind models"""

from django.contrib import admin

from maxmind import models


class NetBlockAdmin(admin.ModelAdmin):
    """Admin for netblock"""

    list_display = ["network", "ip_start", "ip_end", "is_ipv6"]
    list_filter = ["is_ipv6"]
    search_fields = ["ip_start", "ip_end", "network"]


admin.site.register(models.Geoname)
admin.site.register(models.NetBlock, NetBlockAdmin)
