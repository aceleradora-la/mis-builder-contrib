# Copyright 2018 Tecnativa - Ernesto Tejeda
# Copyright 2026 Aceleradora LA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import SQL

VIEW_NAME = "mis_account_analytic_line"
SOURCE_TABLE = "account_analytic_line"


class MisAccountAnalyticLine(models.Model):
    _name = "mis.account.analytic.line"
    _auto = False
    _description = "MIS Account Analytic Line"

    date = fields.Date()
    analytic_line_id = fields.Many2one(
        string="Analytic entry", comodel_name="account.analytic.line"
    )
    account_id = fields.Many2one(string="Account", comodel_name="account.account")
    analytic_account_id = fields.Many2one(
        string="Analytic Account", comodel_name="account.analytic.account"
    )
    company_id = fields.Many2one(string="Company", comodel_name="res.company")
    balance = fields.Float()
    debit = fields.Float()
    credit = fields.Float()
    state = fields.Selection(
        [("draft", "Unposted"), ("posted", "Posted")], string="Status"
    )

    @api.model
    def _plan_columns(self):
        """Return {column_name: plan} for every root plan but the project one.

        Column names are the same as on ``account.analytic.line``
        (``x_plan<N>_id``), so a domain written in a MIS report is identical to
        the one you would write on the analytic line itself. The project plan is
        already exposed as ``analytic_account_id``.

        Only columns that actually exist on ``account_analytic_line`` are
        returned: when a plan is deleted, Odoo drops its column (``DROP COLUMN
        ... CASCADE``, which also drops this view) and re-enters ``init()``
        before the plan record itself is gone.
        """
        self.env.registry.clear_cache()  # _get_all_plans() is ormcached
        try:
            _project_plan, other_plans = self.env[
                "account.analytic.plan"
            ]._get_all_plans()
        except UserError:
            # analytic.project_plan not set yet (fresh database being built)
            return {}
        existing = tools.sql.table_columns(self.env.cr, SOURCE_TABLE)
        columns = {}
        for plan in other_plans:
            name = plan._strict_column_name()
            if name in existing:
                columns[name] = plan
        return columns

    @api.model
    def _sync_plan_fields(self):
        """Create, rename and drop the manual fields mirroring the analytic plans.

        Do NOT call this from ``init()``: ``ir.model.fields.create()`` and
        ``unlink()`` trigger ``registry.setup_models()`` and ``init_models()``,
        which calls ``init()`` again.
        """
        ir_model_fields = self.env["ir.model.fields"].sudo()
        wanted = self._plan_columns()
        existing = ir_model_fields.search(
            [
                ("model", "=", self._name),
                ("state", "=", "manual"),
                ("name", "=like", r"x\_plan%\_id"),
            ]
        )
        obsolete = existing.filtered(lambda f: f.name not in wanted)
        # No MODULE_UNINSTALL_FLAG on purpose: a regular unlink() reloads the
        # registry and re-runs init(), keeping registry, view and
        # ir.model.fields consistent.
        obsolete.unlink()
        keep = existing - obsolete
        model_id = self.env["ir.model"]._get_id(self._name)
        for name, plan in wanted.items():
            field = keep.filtered(lambda f, n=name: f.name == n)
            if field:
                if field.field_description != plan.name:
                    field.field_description = plan.name
                continue
            ir_model_fields.with_context(update_custom_fields=True).create(
                {
                    "name": name,
                    "field_description": plan.name,
                    "state": "manual",
                    "model": self._name,
                    "model_id": model_id,
                    "ttype": "many2one",
                    "relation": "account.analytic.account",
                    "store": True,
                    "readonly": True,
                }
            )

    def init(self):
        columns = [
            SQL("aal.id AS id"),
            SQL("aal.id AS analytic_line_id"),
            SQL("aal.date AS date"),
            SQL("aal.general_account_id AS account_id"),
            SQL("aal.account_id AS analytic_account_id"),
            SQL("aal.company_id AS company_id"),
            SQL("'posted'::VARCHAR AS state"),
            SQL("CASE WHEN aal.amount >= 0.0 THEN aal.amount ELSE 0.0 END AS credit"),
            SQL(
                "CASE WHEN aal.amount < 0 THEN (aal.amount * -1) ELSE 0.0 END AS debit"
            ),
            SQL("aal.amount AS balance"),
        ]
        columns += [
            SQL("aal.%s AS %s", SQL.identifier(name), SQL.identifier(name))
            for name in self._plan_columns()
        ]
        tools.drop_view_if_exists(self.env.cr, VIEW_NAME)
        self.env.cr.execute(
            SQL(
                "CREATE OR REPLACE VIEW %s AS (SELECT %s FROM %s aal)",
                SQL.identifier(VIEW_NAME),
                SQL(", ").join(columns),
                SQL.identifier(SOURCE_TABLE),
            )
        )
