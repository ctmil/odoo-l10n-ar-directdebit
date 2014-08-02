# -*- coding: utf-8 -*-
from osv import fields,osv
from tools.translate import _
from openerp import netsvc

class account_invoice(osv.osv):
    _inheret = 'account.invoice'

    _columns = {
        'is_directdebit': fields.boolean('Is Direct Debit'),
    }
account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
