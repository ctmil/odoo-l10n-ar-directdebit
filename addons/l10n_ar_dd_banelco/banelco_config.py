# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp
from openerp.tools.translate import _
from openerp.osv import fields, osv

class banelco_config_settings(osv.osv_memory):
    _name = 'banelco.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'banelco_company_id': fields.char('Company ID in Banelco DirectDebit', required=True)
    }

    def _check_banelco_company_id(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.banelco_company_id:
                if len(obj.banelco_company_id) != 4:
                    return False
                try:
                    num = int(obj.banelco_company_id)
                except ValueError:
                    return False
        return True

    _constraints = [
        (_check_banelco_company_id, 'The company id should be a four-digit number.', ['banelco_company_id']),
    ]

    def get_default_banelco_company_id(self, cr, uid, fields, context=None):
        icp = self.pool.get('ir.config_parameter')
        return {
            'banelco_company_id': icp.get_param(cr, uid, 'banelco_company_id', '')
        }

    def set_banelco_company_id(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)
        icp = self.pool.get('ir.config_parameter')
        icp.set_param(cr, uid, 'banelco_company_id', config.banelco_company_id)

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
