# -*- coding: utf-8 -*-

from openerp.osv import fields,osv
from openerp.tools.translate import _
from openerp import netsvc
import time
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class directdebit_response(osv.osv):
    _name = 'directdebit.response'
    _description = 'Direct debit response'

    _columns = {
        'name': fields.char('Name'),
        'code': fields.char('Code', size=3),
        'description': fields.text('Description'),
        'type': fields.selection([('ok','No error'),
                                  ('temporal','Temporal error'),
                                  ('fatal', 'Fatal error'),
                                  ('unknown', 'Unknown error')], 'Response type'),
        'bank_id': fields.many2one('res.bank', 'Related error bank'),
    }
directdebit_response()

def cbu_validate(cbu):
    if type(cbu) == int:
        cbu = "%022d" % cbu
    cbu = cbu.strip()
    if len(cbu) != 22:
        return False
    s1 = sum( int(a)*b for a,b in zip(cbu[0:7],(7,1,3,9,7,1,3)) )
    d1 = (10 - s1) % 10
    if d1 != int(cbu[7]):
        return False
    s2 = sum( int(a)*b for a,b in zip(cbu[8:-1],(3,9,7,1,3,9,7,1,3,9,7,1,3)) )
    d2 = (10 - s2) % 10
    if d2 != int(cbu[-1]):
        return False
    return True

class directdebit_line(osv.osv):
    _name = 'directdebit.communication.line'
    _description = 'Direct debit lines'

    def onchange_invoice_id(self, cr, uid, ids, invoice_id, context=None):
        invoice_obj = self.pool.get('account.invoice')
        partner_obj = self.pool.get('res.partner')
        r = {}
        if invoice_id:
            invoice = invoice_obj.browse(cr, uid, invoice_id)
            bank_ids = invoice.partner_id.bank_ids
            r['partner_bank_id'] = bank_ids and bank_ids[0].id or False
        return {'value': r}
    
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice', domain="[('state','=','open'),('type','=','out_invoice')]"),
        #'response_id': fields.many2one('directdebit.communication.line', 'Response line'),
        #'answer_id': fields.one2many('directdebit.communication.line', 'response_id', 'Answer line'),
        'communication_id': fields.many2one('directdebit.communication', 'Communication'),
        #'bank_id': fields.many2one('res.bank', 'Bank'),
        'partner_id': fields.related('invoice_id', 'partner_id',
                                     type="many2one", relation="res.partner",
                                     string="Partner", readonly=True, store=False),
        'amount_total': fields.related('invoice_id', 'amount_total', type="float",
                                     string="Amount", readonly=True, store=False),
        'partner_bank_id': fields.many2one('res.partner.bank', 'Source Bank Account',
                                           domain="[('partner_id','=',partner_id)]",
                                           context="{'default_partner_id': partner_id}", required=True),
        'operation_code': fields.char('Operation code', size=2),
        'date_due': fields.date('Due date', size=6),
        'directdebit_company_code': fields.char('Bank Company Code', size=6),
        'directdebit_partner_code': fields.char('Partner Company Code', size=21),
        'directdebit_currency_code': fields.selection([('P','Argentinian Pesos'),('D', 'US Dollars')], 'Currency Code'),
        'cbu': fields.char('CBU', size=22),
        'amount': fields.float('Amount', digits=(8,2)),
        'cuit': fields.char('CUIT', size=11),
        'description': fields.char('Description', size=62),
        'response_code': fields.many2one('directdebit.response', 'Response code'),
    }
directdebit_line()

class directdebit_communication(osv.osv):
    _name = 'directdebit.communication'
    _description = 'Communication to recived/send from/to the bank'

    _columns = {
        'name': fields.char('Name', required=True),
        'line_description': fields.char('Description', help="Description of all lines. If not set use the invoice name.", size=10),
        'open_date': fields.datetime('Open Date'),
        'debit_date': fields.date('Debit date'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'partner_bank_id': fields.many2one('res.partner.bank', 'Target Bank Account',
                                           domain="[('company_id','=',company_id)]",
                                           context="{'default_company_id':company_id}",
                                          required=True),
        'line_ids': fields.one2many('directdebit.communication.line', 'communication_id', 'Lines', ondelete='cascade'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('done','Done'),('cancel','Canceled')], string="State"),
        'traffic': fields.selection(
            [('EB', 'From company to bank'),
             ('BE', 'From bank to company')],
            'Information Traffic'),
    }

    def _default_line_ids(self, cr, uid, context=None):
        invoice_obj = self.pool.get('account.invoice')
        context = context or {}
        r = []

        def get_partner_bank_id(invoice_id):
            par = invoice_obj.browse(cr, uid, inv_id).partner_id
            accounts = par.bank_ids and [ account.id for account in par.bank_ids if account.bank and account.bank.bcra_code and cbu_validate(account.acc_number) ]
            if accounts:
                return accounts[0]
            else:
                return False

        if context.get('active_model', False) == 'account.invoice':
            invoice_ids = context.get('active_ids', [])
            r = [(0,0, {'invoice_id': inv_id,
                        'partner_bank_id': get_partner_bank_id(inv_id),
                       }) for inv_id in invoice_ids]
        return r

    _defaults = {
        'open_date': lambda *a: datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'debit_date': lambda *a: (datetime.now() + timedelta(days=3)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        'company_id': lambda self, cr, uid, *a: self.pool.get('res.users').browse(cr, uid, uid).company_id.id,
        'state': 'draft',
        'line_ids': _default_line_ids,
    }

    def do_request(self, cr, uid, ids, context=None):
        if self.validate(cr, uid, ids, context=context):
            self.write(cr, uid, ids, {'state': 'open'})
        return True

    def do_pool(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'})
        pass

    def do_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        pass

    def do_todraft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'})
        pass

    def validate(self, cr, uid, ids, context=None):
        for com in self.browse(cr, uid, ids):
            if not (datetime.strptime(com.debit_date,
                                      DEFAULT_SERVER_DATE_FORMAT) -
                    datetime.now()).days >= 2:
                raise osv.except_osv(_("Error"), _("Debit date must be 3 days more than today."))
            if not com.partner_bank_id.bank.bcra_code:
                raise osv.except_osv(_("Error"), _("Your Target Bank Account has not BCRA code assigned.\nCheck the <a href='http://www.bcra.gob.ar/sisfin/sf020101.asp?bco=AAA20&tipo=3'>value</a> and setup before continue."))
            if not com.partner_bank_id.directdebit_code:
                raise osv.except_osv(_("Error"), _("Your Target Bank Account has not a direct debit code assigned.\nPlease ask to your bank to setup before continue."))
            for line in com.line_ids:
                if not line.invoice_id.state == "open":
                    raise osv.except_osv(_("Error"),
                                         _("Invoice %s is not Open.\nPlease, select an Open Invoice or Validate before continue.") % line.invoice_id.number)
                if not line.partner_bank_id:
                    raise osv.except_osv(_("Error"),
                                         _("No bank account assigned to %s.\nSetup before continue.") % line.invoice_id.number)
                if not line.partner_bank_id.bank:
                    raise osv.except_osv(_("Error"),
                                         _("No bank assigned to the bank account for %s.\nSetup before continue.") % line.invoice_id.number)
                if not line.partner_bank_id.bank.bcra_code:
                    raise osv.except_osv(_("Error"),
                                         _("The bank associated to the line %s has not BCRA code assigned.\nCheck the value for %s in the BCRA and setup before continue.") %
                                         (line.partner_bank_id.bank.name, line.invoice_id.number))
                if not (line.partner_bank_id.acc_number and cbu_validate(line.partner_bank_id.acc_number)):
                    raise osv.except_osv(_("Error"),
                                         _("The bank account associated to %s is not a valid CBU.\nCheck it or ask to your partner and setup before continue.") % line.invoice_id.number)
        
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
