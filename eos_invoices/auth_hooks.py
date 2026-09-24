from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls
from .views import dashboard_overview


class InvoicesMenuItem(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            _("Invoices"),
            "fas fa-file-invoice-dollar",
            "eos_invoices:index",
            navactive=["eos_invoices:"],
        )

    def render(self, request):
        user = request.user
        if user.has_perm("eos_invoices.basic_access"):
            self.url_name = "eos_invoices:index"
        elif user.has_perm("eos_invoices.manage_sources"):
            # an admin who is no CEO has no overview of their own
            self.url_name = "eos_invoices:admin"
        else:
            return ""

        return MenuItemHook.render(self, request)


@hooks.register("menu_item_hook")
def register_menu():
    return InvoicesMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "eos_invoices", r"^eos_invoices/")


class InvoicesDashboardHook(hooks.DashboardItemHook):
    def __init__(self):
        hooks.DashboardItemHook.__init__(self, dashboard_overview)


@hooks.register("dashboard_hook")
def register_dashboard():
    return InvoicesDashboardHook()
