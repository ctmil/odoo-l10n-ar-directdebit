# -*- coding: utf-8 -*-
from openerp.osv import fields,osv
from openerp.tools.translate import _
from openerp import netsvc
from datetime import date, datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as D_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
import csv
import re
from StringIO import StringIO
import string
try:
    import simplejson as json
except:
    import json

def to_numeric(value):
    return int(value) if value and value.isnumeric() else 0


class directdebit_communication(osv.osv):
    _name = 'directdebit.communication'
    _inherit = 'directdebit.communication'

    def _valid_alphanumeric(self, text):

        # Replace "dangerous" characters
        replacements = {138: 's', 140: 'O', 142: 'z', 154: 's', 156: 'o', 158: 'z', 159: 'Y', 192: 'A', 193: 'A', 194: 'A', 195: 'a', 196: 'A', 197: 'Aa', 198: 'E', 199: 'C', 200: 'E', 201: 'E', 202: 'E', 203: 'E', 204: 'I', 205: 'I', 206: 'I', 207: 'I', 208: 'Th', 209: 'N', 210: 'O', 211: 'O', 212: 'O', 213: 'O', 214: 'O', 215: 'x', 216: 'O', 217: 'U', 218: 'U', 219: 'U', 220: 'U', 222: 'th', 221: 'Y', 223: 's', 224: 'a', 225: 'a', 226: 'a', 227: 'a', 228: 'ae', 229: 'aa', 230: 'ae', 231: 'c', 232: 'e', 233: 'e', 234: 'e', 235: 'e', 236: 'i', 237: 'i', 238: 'i', 239: 'i', 240: 'th', 241: 'n', 242: 'o', 243: 'o', 244: 'o', 245: 'o', 246: 'oe', 248: 'oe', 249: 'u', 250: 'u', 251: 'u', 252: 'u', 253: 'y', 254: 'Th', 255: 'y'}

        text = text.decode('utf-8')
        for k in replacements:
            text = text.replace(unichr(k), replacements[k])

        # Uppercase
        text = text.upper()

        # Allow unly "safe" characters
        valid = string.ascii_uppercase + string.digits + ' ()*.:;/-'
        for char in text:
            if not char in valid:
                text = text.replace(char, '')
        return text

    def _get_banelco_output(self, cr, uid, ids, fields, args, context=None):
        r = self.generate_output(cr, uid, ids, context=context)
        return r

    def _get_banelco_output_filename(self, cr, uid, ids, fields, args, context=None):
        import pdb; pdb.set_trace()
        r = {}
        now = datetime.now()
        icp = self.pool.get('ir.config_parameter')
        banelco_company_id = icp.get_param(cr, uid, 'banelco_company_id', '')
        for com in self.browse(cr, uid, ids):
            r[com.id] = "FAC%s%s.csv" % (banelco_company_id, now.strftime('%m%d%Y'))

        return r

    def _get_banelco_input(self, cr, uid, ids, fields, args, context=None):
        return {}

    def _set_banelco_input(self, cr, uid, ids,
                             field_name, field_value, arg, context=None):
        return None
        dd_line_obj = self.pool.get('directdebit.communication.line')
        dd_input = field_value.decode('base64')
        if dd_input:
            dd_input = dd_input.split('\n')
            for line in dd_input:
                #ml = re_be_communication_line.match(line)
                if ml:
                    data = ml.groupdict()
                    par_id = int(data['partner_id'])
                    amount = float(data['amount'])
                    dd_line_ids = dd_line_obj.search(cr, uid, [
                        ('id', '=', ids),
                        ('partner_id', '=', par_id),
                        ('amount', '=', amount)])
                    if len(dd_line_ids) == 1:
                        dd_line_obj.write(
                            cr, uid, dd_line_ids,
                            {'response_code': data['response_code']})

    _columns = {
        'banelco_output': fields.function(_get_banelco_output, type="binary", mode="model", string="File to send to Banelco", readonly="True", store=False),
        'banelco_output_filename': fields.function(_get_banelco_output_filename, type="char", mode="model", string="Filename to Banelco", store=False),
        'banelco_input': fields.function(_get_banelco_input, fnct_inv = _set_banelco_input, type="binary", mode="model", string="File from Banelco", store=False),
    }

    def generate_output(self, cr, uid, ids, context=None):
        r = {}
        pt_obj = self.pool.get('account.payment.term')
        for com in self.browse(cr, uid, ids):
            if com.state == 'draft':
                r[com.id] = None
                continue

            out = StringIO()
            writer = csv.writer(out, dialect='excel')
            for l in com.line_ids:
                ol = []
                ref_number = "%012d" % l.partner_id.id
                ol.append(ref_number)
                bill_id = l.invoice_id.id
                ol.append(bill_id)

                # Calculate due dates:
                # If invoice has a date, calculate dues an amounts based on payment term
                if l.invoice_id.date_invoice:
                    ref_date = l.invoice_id.date_invoice
                    payment_term_id = l.invoice_id.payment_term.id
                    if payment_term_id:
                        pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=ref_date)
                        if pterm_list:
                            pterm_list.sort()
                            dues_amounts = []
                            for pterm in pterm_list[:3]:
                                date = pterm[0] # YYYY-MM-DD
                                year = date[:4]
                                month = date[5:7]
                                day = date[-2:]
                                
                                dues_amounts.append(('%s%s%s'%(day,month,year), pterm[-1]))

                    else:
                        # No payment term
                        date = datetime.strptime(ref_date, D_FORMAT).strftime("%d%m%Y")
                        dues_amounts = [(date, l.invoice_id.amount_total), None, None]

#                elif l.invoice_id.date_due:
#                    # If invoice has no date, but a due date, set a single amount and due date
#                    ref_date = l.invoice_id.date_due
#                    date = datetime.strptime(ref_date, D_FORMAT).strftime("%d%m%Y")
#                    dues_amounts = [(date, l.invoice_id.amount_total), None, None]
#                elif l.communication_id.debit_date:
#                    ref_date = l.communication_id.debit_date
#                    # If invoice has neither date nor due date, set a single amount and due date based
#                    # on communication debit_date
#                    date = datetime.strptime(ref_date, D_FORMAT).strftime("%d%m%Y")
#                    dues_amounts = [(date, l.invoice_id.amount_total), None, None]
#                else:
#                    # No reference date, skip it
#                    continue

                # Get first 3 due dates and amounts
                for da in dues_amounts[:3]:
                    date_due = ""
                    amount = ""
                    if not da is None:
                        date_due = da[0]
                        amount = da[1]
                        amount_int = int(amount)
                        amount_dec = int((amount - amount_int)*100)
                        amount = "%s,%s" % (amount_int, amount_dec)
                    ol.append(date_due)
                    ol.append(amount)


                prev_ref = ""
                ol.append(prev_ref)

                msg_ticket = self._valid_alphanumeric(l.invoice_id.number)
                ol.append(msg_ticket)

                msg_screen = self._valid_alphanumeric(l.invoice_id.number)
                ol.append(msg_screen)

                code_bar = ""
                ol.append(code_bar)

                writer.writerow(ol)

            r[com.id] = out.getvalue().encode('base64')
        return r

    def read_input(self, cr, uid, ids, context=None):
        return {}

directdebit_communication()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
