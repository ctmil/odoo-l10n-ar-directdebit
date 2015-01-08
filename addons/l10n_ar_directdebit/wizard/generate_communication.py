# -*- coding: utf-8 -*-
from osv import fields,osv
from tools.translate import _
from openerp import netsvc

class wiz_create_communication(osv.osv_memory):
    _name = 'directdebit.create_communication'
    _description = 'Create communication from invoices'

    _columns = {
        'name': fields.char('Name', required=True),
        'line_description': fields.char('Description', help="Description of all lines. If not set use the invoice name.", size=10),
        'open_date': fields.datetime('Open Date'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'partner_bank_id': fields.many2one('res.partner.bank', 'Target Bank Account',
                                           domain="[('company_id','=',company_id)]", context="{'default_company_id':company_id}"),
    }

    _defaults = {
        'open_date': lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'company_id': lambda self, cr, uid, *a: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
    }

    def execute(self, cr, uid, ids, context=None):
        return {}

wiz_create_communication()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

