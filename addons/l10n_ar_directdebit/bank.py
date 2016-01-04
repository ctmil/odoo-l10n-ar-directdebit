# -*- coding: utf-8 -*-
from openerp import fields, models


class partner_bank(models.Model):
    _name = 'res.partner.bank'
    _inherit = 'res.partner.bank'

    directdebit_code = fields.Integer(
        'Direct Debit Identification',
        help='Unique Identification Code assigned by the bank to the'
        ' partner to execute Direct Debits.')
    directdebit_uri_publish = fields.Char(
        'Publish Direct Debit URI')
    directdebit_uri_retrieve = fields.Char(
        'Retrieve Direct Debit URI')
    directdebit_user = fields.Char(
        'Direct Debit Credential')
    directdebit_password = fields.Char(
        'Direct Debit Password',
        password=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
