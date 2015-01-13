# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc

class partner_bank(osv.osv):
    _name = 'res.partner.bank'
    _inherit = 'res.partner.bank'

    _columns = {
        'directdebit_code': fields.integer('Direct Debit Identification',
                                   help="Unique Identification Code assigned by the bank to the partner to execute Direct Debits."),
        'directdebit_user': fields.char('Direct Debit Credential'),
        'directdebit_password': fields.char('Direct Debit Password',
                                            password=True),
    }
partner_bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
