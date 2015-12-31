# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class directdebit_response(models.Model):
    _name = 'directdebit.response'
    _description = 'Direct debit response'

    name = fields.Char('Name')
    code = fields.Char('Code', size=3)
    description = fields.Text('Description')
    type = fields.Selection([('ok', 'No error'),
                             ('temporal', 'Temporal error'),
                             ('fatal', 'Fatal error'),
                             ('unknown', 'Unknown error')], 'Response type')
    bank_id = fields.Many2one('res.bank', 'Related error bank')


class directdebit_line(models.Model):
    _name = 'directdebit.communication.line'
    _description = 'Direct debit lines'

    @api.onchange('invoice_id')
    def invoice_id_change(self):
        bank_ids = self.invoice_id.partner_id.bank_ids.ids + [False]
        self.partner_bank_id = bank_ids[0]

    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice',
        domain="[('state','=','open'),('type','=','out_invoice')]")
    communication_id = fields.Many2one(
        'directdebit.communication',
        'Communication')
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string="Partner", readonly=True, store=False)
    partner_bank_id = fields.Many2one(
        'res.partner.bank', 'Source Bank Account',
        domain="[('partner_id','=',partner_id)]",
        context="{'default_partner_id': partner_id}", required=True)
    date_due = fields.Date(
        'Due date', size=6)
    directdebit_company_code = fields.Char(
        'Bank Company Code', size=6)
    directdebit_partner_code = fields.Char(
        'Partner Company Code', size=21)
    directdebit_currency_code = fields.Selection(
        [('P', 'Argentinian Pesos'), ('D', 'US Dollars')],
        'Currency Code'),
    amount = fields.Float(
        string='Amount',
        digits=dp.get_precision('Account'),
        compute='_compute_amount',
        store=True, help="Amount to debit")
    description = fields.Char('Description', size=62)
    response_code = fields.Many2one('directdebit.response', 'Response code'),

    @api.one
    @api.depends('invoice_id.amount_total', 'invoice_id.residual',
                 'communication_id.debit_residue')
    def calc_amount(self):
        self.amount = (
            self.invoice_id.amount_total
            if (self.communication_id.debit_residue)
            else self.invoice_id.residual)


class invoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    @api.model
    def create_communication(self):
        ids = self.env.context["active_ids"]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'directdebit.communication',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'invoices': ids},
        }


class directdebit_communication(models.Model):
    _name = 'directdebit.communication'
    _description = 'Communication to recived/send from/to the bank'

    @api.multi
    def _default_line_ids(self):
        context = self.env.context

        invoice_pool = self.env['account.invoice']
        r = []

        def get_partner_bank_id(inv_id):
            par = invoice_pool.browse(inv_id).partner_id
            accounts = par.bank_ids and [account.id
                                         for account in par.bank_ids
                                         if account.bank
                                         and account.bank.bcra_code
                                         and account.is_valid_cbu()]
            if accounts:
                return accounts[0]
            else:
                return False

        if context.get('invoices', False):
            invoice_ids = context.get('invoices', [])
            r = [(0, 0, {'invoice_id': inv_id,
                         'partner_bank_id': get_partner_bank_id(inv_id)})
                 for inv_id in invoice_ids]
        return r

    name = fields.Char(
        'Name',
        required=True)
    open_date = fields.Datetime(
        'Open Date',
        default=lambda *a: datetime.now().strftime(DATETIME_FORMAT)
    )
    debit_date = fields.Date(
        'Debit date',
        default=lambda *a: (datetime.now() + timedelta(days=3)
                            ).strftime(DATETIME_FORMAT)
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.user.company_id.id,
        required=True,
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        'Target Bank Account',
        domain="[('company_id','=',company_id)]",
        context="{'default_company_id':company_id}",
        required=True)
    line_ids = fields.One2many(
        'directdebit.communication.line',
        'communication_id',
        'Lines',
        default=_default_line_ids,
        ondelete='cascade')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Open'),
         ('done', 'Done'),
         ('cancel', 'Canceled')],
        string="State",
        default='draft')
    traffic = fields.Selection(
        [('EB', 'From company to bank'),
         ('BE', 'From bank to company')],
        'Information Traffic')
    debit_residue = fields.Boolean(
        'Debit residue until total',
        default=True
    )

    def do_request(self, cr, uid, ids, context=None):
        if self.validate(cr, uid, ids, context=context):
            self.write(cr, uid, ids, {'state': 'open'})
        return True

    def do_pool(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'})
        pass

    def do_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        pass

    def do_todraft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'})
        pass

    @api.multi
    def _validate_date(self):
        self.ensure_one()
        if not (datetime.strptime(self.debit_date, DATE_FORMAT) -
                datetime.now()).days >= 2:
            raise Warning(
                _("Error\nDebit date must be 3 days more than today."))

    @api.multi
    def _validate_bank(self):
        self.ensure_one()
        if not self.partner_bank_id.bank.bcra_code:
            raise Warning(
                _("Error\n"
                    "Your Target Bank Account has not BCRA code assigned.\n"
                    "Check the "
                    "<a href='http://www.bcra.gob.ar/sisfin/sf020101.asp"
                    "?bco=AAA20&tipo=3'>value</a>"
                    " and setup before continue."))
        if not self.partner_bank_id.directdebit_code:
            raise Warning(
                _("Error\n"
                    "Your Target Bank Account has not a direct debit"
                    " code assigned.\n"
                    "Please ask to your bank to setup before continue."))

    @api.multi
    def _validate_lines(self):
        self.ensure_one()
        for line in self.line_ids:
            if not line.invoice_id.state == "open":
                raise Warning(
                    _("Error\nInvoice %s is not Open.\n"
                        "Please, select an Open Invoice or Validate"
                        " before continue.") % line.invoice_id.number)
            if not line.partner_bank_id:
                raise Warning(
                    _("Error\nNo bank account assigned to %s.\n"
                        "Setup before continue.") % line.invoice_id.number)
            if not line.partner_bank_id.bank:
                raise Warning(
                    _("Error\nNo bank assigned to the bank account for %s."
                        "\nSetup before continue.") % line.invoice_id.number)
            if not line.partner_bank_id.bank.bcra_code:
                raise Warning(
                    _("Error\nThe bank associated to the line %s has not"
                        " BCRA code assigned.\nCheck the value for %s in"
                        " the BCRA and setup before continue.")
                    % (line.partner_bank_id.bank.name,
                        line.invoice_id.number))
            if not (line.partner_bank_id.acc_number and
                    line.partner_bank_id.is_valid_cbu()):
                raise Warning(
                    _("Error\n"
                        "The bank account associated to %s is not a valid"
                        " CBU.\nCheck it or ask to your partner and setup"
                        " before continue.") % line.invoice_id.number)

    @api.multi
    def validate(self):
        for com in self:
            com._validate_date()
            com._validate_bank()
            com._validate_lines()

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
