# Copyright 2026 Aceleradora LA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    def _sync_all_plan_column(self):
        """Keep ``mis.account.analytic.line`` in sync with the analytic plans.

        Odoo calls this from ``_inverse_name`` and ``_inverse_parent_id``, that
        is whenever a plan is created, renamed or reparented.
        """
        res = super()._sync_all_plan_column()
        mis_line = self.env["mis.account.analytic.line"].sudo()
        mis_line._sync_plan_fields()
        mis_line.init()
        return res
