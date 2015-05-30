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
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.translate import _
from openerp.osv import fields, osv

class banelco_config_settings(osv.osv_memory):
    _name = 'banelco.directdebit.communication'
    _inherit = 'res.config.settings'

    _columns = {
        'banelco_company_id': fields.char('Company ID in Banelco DirectDebit', required=True)
    }

    def _check_account_gain(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.income_currency_exchange_account_id.company_id and obj.company_id != obj.income_currency_exchange_account_id.company_id:
                return False
        return True

    def _check_account_loss(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.expense_currency_exchange_account_id.company_id and obj.company_id != obj.expense_currency_exchange_account_id.company_id:
                return False
        return True

    def create(self, cr, uid, values, context=None):
        id = super(banelco_config_settings, self).create(cr, uid, values, context)
        # Hack: to avoid some nasty bug, related fields are not written upon record creation.
        # Hence we write on those fields here.
        vals = {}
        for fname, field in self._columns.iteritems():
            if isinstance(field, fields.related) and fname in values:
                vals[fname] = values[fname]
        self.write(cr, uid, [id], vals, context)
        return id

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
