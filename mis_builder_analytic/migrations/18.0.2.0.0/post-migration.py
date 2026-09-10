# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    mis_line = env["mis.account.analytic.line"]
    mis_line._sync_plan_fields()
    mis_line.init()
