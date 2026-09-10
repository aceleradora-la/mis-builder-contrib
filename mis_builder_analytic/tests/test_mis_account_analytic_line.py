# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase

MODEL = "mis.account.analytic.line"
VIEW = "mis_account_analytic_line"


class TestMisAccountAnalyticLine(TransactionCase):
    def _view_columns(self):
        self.env.cr.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s",
            (VIEW,),
        )
        return {row[0] for row in self.env.cr.fetchall()}

    def _manual_field(self, column):
        return (
            self.env["ir.model.fields"]
            .sudo()
            .search([("model", "=", MODEL), ("name", "=", column)])
        )

    def _create_plan(self, name):
        plan = self.env["account.analytic.plan"].create({"name": name})
        return plan, plan._strict_column_name()

    def test_existing_plans_are_exposed(self):
        mis_line = self.env[MODEL]
        view_columns = self._view_columns()
        for column in mis_line._plan_columns():
            self.assertIn(column, view_columns, f"{column} missing from the view")
            self.assertIn(column, mis_line._fields)
            self.assertTrue(self._manual_field(column))
            # must not raise
            mis_line.search([(column, "=", False)], limit=1)

    def test_project_plan_is_not_duplicated(self):
        mis_line = self.env[MODEL]
        self.assertNotIn("account_id", mis_line._plan_columns())
        self.assertEqual(mis_line._fields["account_id"].comodel_name, "account.account")

    def test_new_plan_is_synced(self):
        _plan, column = self._create_plan("MIS Test Plan")
        mis_line = self.env[MODEL]
        self.assertIn(column, mis_line._plan_columns())
        self.assertIn(column, self._view_columns())
        field = self._manual_field(column)
        self.assertTrue(field)
        self.assertEqual(field.field_description, "MIS Test Plan")
        self.assertEqual(field.relation, "account.analytic.account")
        self.assertTrue(field.store)

    def test_renamed_plan_is_synced(self):
        plan, column = self._create_plan("MIS Test Plan")
        plan.name = "MIS Renamed Plan"
        self.assertEqual(self._manual_field(column).field_description, plan.name)

    def test_deleted_plan_is_dropped(self):
        plan, column = self._create_plan("MIS Test Plan")
        self.assertIn(column, self._view_columns())
        plan.unlink()
        self.assertNotIn(column, self._view_columns())
        self.assertFalse(self._manual_field(column))
        # the view must survive the DROP COLUMN ... CASCADE done by Odoo
        self.env[MODEL].search([], limit=1)

    def test_plan_column_values(self):
        plan, column = self._create_plan("MIS Test Plan")
        accounts = self.env["account.analytic.account"].create(
            [
                {"name": "MIS A", "plan_id": plan.id},
                {"name": "MIS B", "plan_id": plan.id},
            ]
        )
        lines = self.env["account.analytic.line"].create(
            [
                {"name": "60%", "amount": 60.0, column: accounts[0].id},
                {"name": "40%", "amount": 40.0, column: accounts[1].id},
            ]
        )
        self.env.cr.execute(
            f"SELECT {column}, balance FROM {VIEW} WHERE id IN %s ORDER BY id",
            (tuple(lines.ids),),
        )
        self.assertEqual(
            self.env.cr.fetchall(),
            [(accounts[0].id, 60.0), (accounts[1].id, 40.0)],
        )
        mis_line = self.env[MODEL]
        self.assertEqual(
            mis_line.search([(column, "=", accounts[0].id)]).mapped("balance"),
            [60.0],
        )
        self.assertEqual(
            mis_line.search([(column, "in", accounts.ids)]).mapped("balance"),
            [60.0, 40.0],
        )
