# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class wiz_create_communication(models.TransientModel):
    _name = 'directdebit.wiz_create_communication'
    _description = 'Create communication from invoices'

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

        invoice_ids = context.get('invoices', context.get('active_ids', False))

        if invoice_ids:
            r = [(0, 0, {'invoice_id': inv_id,
                         'partner_bank_id': get_partner_bank_id(inv_id)})
                 for inv_id in invoice_ids]
        return r

    name = fields.Char(
        'Name',
        required=True)
    open_date = fields.Datetime(
        'Open Date',
        default=lambda *a: datetime.now().strftime(DATETIME_FORMAT))
    debit_date = fields.Date(
        'Debit date',
        default=lambda *a: (datetime.now() + timedelta(days=3)
                            ).strftime(DATETIME_FORMAT))
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.user.company_id.id,
        required=True)
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        'Target Bank Account',
        domain="[('company_id','=',company_id)]",
        context="{'default_company_id':company_id}",
        required=True)
    debit_residue = fields.Boolean(
        'Debit residue until total',
        default=True)
    line_description = fields.Char(
        'Description',
        help='Description for all lines. If not set use the invoice name.',
        size=10)

    @api.multi
    def execute(self):
        self.ensure_one()

        com_obj = self.env['directdebit.communication']

        com = com_obj.create({
            'name': self.name,
            'open_date': self.open_date,
            'debit_date': self.debit_date,
            'company_id': self.company_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'line_ids': self._default_line_ids(),
            'debit_residue': self.debit_residue,
            'line_description': self.line_description,
            'traffic': 'EB',
        })

        return {
            'name': _('New Communication'),
            'res_model': 'directdebit.communication',
            'res_id': com.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
        }

wiz_create_communication()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
