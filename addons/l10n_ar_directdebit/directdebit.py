# -*- coding: utf-8 -*-

from osv import fields,osv
from tools.translate import _
from openerp import netsvc

class directdebit_line(osv.osv):
    _name = 'credicoop_dd.comunication.line'
    _description = 'Direct debit lines'
    
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'traffic': fields.selection(
            [('EB', 'From company to bank'),
             ('BE', 'From bank to company')],
            'Information Traffic'),
        'bank_code': fields.char('Bank code'. size=3),
        'operation_code': fields.char('Regitry code', size=2),
        'date_due': fields.char('Due date', size=6),
        'directdebit_company_code': fields.char('Bank Company Code', size=6),
        'directdebit_partner_code': fields.char('Partner Company Code', size=21),
        'directdebit_currency_code': fields.select([('P','Argentinian Pesos'),('D', 'US Dollars')], 'Currency Code'),
        'cbu': fields.char('CBU', size=22),
        'amount': fields.float('Amount', digits=(8,2)),
        'cuit': fields.char('CUIT', size=11),
    }

class directdebit_communication(osv.osv):
    _name = 'credicoop_dd.communication'
    _description = 'Communication to recived/send from/to the bank'

    _columns = {

    }




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
