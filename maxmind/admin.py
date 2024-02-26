"""Admin for maxmind models"""

from django.contrib import admin

from maxmind.models import Geoname, NetBlock


@admin.register(NetBlock)
class NetBlockAdmin(admin.ModelAdmin):
    """Admin for netblock"""

    list_display = ["network", "ip_start", "ip_end", "is_ipv6"]
    list_filter = ["is_ipv6"]
    search_fields = ["ip_start", "ip_end", "network"]


admin.site.register(Geoname)
