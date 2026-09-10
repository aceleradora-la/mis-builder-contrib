This module allows you to create a MIS report using Analytic entries as
data source

Every root analytic plan is exposed as a column of the MIS analytic line model,
using the same field name as on ``account.analytic.line`` (``x_plan<N>_id``), so
report columns and KPI expressions can be filtered by cost center, business unit
or any other plan. Columns are created, renamed and dropped automatically when
analytic plans change.
