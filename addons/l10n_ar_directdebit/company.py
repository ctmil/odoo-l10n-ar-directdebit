# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc

class company(osv.osv):
    _inheret = 'res.company'

    _columns = {
        'directdebit_company_code': fields.char('Bank Company Code'),
    }
company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
