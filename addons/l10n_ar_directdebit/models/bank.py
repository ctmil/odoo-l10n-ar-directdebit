# -*- coding: utf-8 -*-
from openerp import fields, api, models
from openerp.exceptions import ValidationError


class partner_bank(models.Model):
    _name = 'res.partner.bank'
    _inherit = 'res.partner.bank'

    use_directdebit = fields.Boolean('Use Direct Debit')
    directdebit_code = fields.Char(
        'Direct Debit Identification',
        help='Unique Identification Code assigned by the bank to the'
        ' partner to execute Direct Debits.')
    directdebit_username = fields.Char('Direct Debit Credential')
    directdebit_password = fields.Char('Direct Debit Password')
    directdebit_request_uri = fields.Char('Direct Debit Request URI')
    directdebit_response_uri = fields.Char('Direct Debit Response URI')

    @api.constrains('use_directdebit')
    def _check_use_directdebit(self):
        self.ensure_one()

        if self.use_directdebit:
            check = self.directdebit_request_uri \
                and self.directdebit_response_uri
            if not check:
                raise ValidationError("Set Direct Debit request and response"
                                      "URIs to connect to bank")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
