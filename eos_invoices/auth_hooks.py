from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


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
            # somebody who only maintains the sources would otherwise be sent
            # to an overview they are not allowed to open
            self.url_name = "eos_invoices:sources"
        else:
            return ""

        return MenuItemHook.render(self, request)


@hooks.register("menu_item_hook")
def register_menu():
    return InvoicesMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "eos_invoices", r"^eos_invoices/")
