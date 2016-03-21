# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as D_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
import re
from StringIO import StringIO
import logging

_logger = logging.getLogger(__name__)

eb_communication_line = "{bank_code:03d}"\
                        "{operation_code:02d}"\
                        "{date_due:6s}"\
                        "{directdebit_code:05d}"\
                        "{partner_id:<22s}"\
                        "{currency_code:1s}"\
                        "{cbu:022d}"\
                        "{amount:010d}"\
                        "{cuit:011d}"\
                        "{description:<10s}"\
                        "{document_id:<15s}\n"

be_communication_line = r"(?P<bank_id>.{3})"\
                        r"(?P<operation_code>.{2})"\
                        r"(?P<date_due>.{6})"\
                        r"(?P<directdebit_code>.{5})"\
                        r"(?P<partner_id>.{22})"\
                        r"(?P<currency_code>.{1})"\
                        r"(?P<cbu>.{22})"\
                        r"(?P<amount>.{10})"\
                        r"(?P<cuit>.{11})"\
                        r"(?P<description>.{10})"\
                        r"(?P<document_id>.{15})"\
                        r"(?P<ref_id>.{15})"\
                        r"(?P<new_cbu>.{22})"\
                        r"(?P<response_code>.{3})"

re_be_communication_line = re.compile(be_communication_line)

currency_code_map = {
    'ARS': 'P',
    'USD': 'D',
}

ignore_symbol_chars = '-/\\'

response_code_message = {
    'R02': 'Cuenta cerrada o suspendida',
    'R03': 'Cuenta inexistente',
    'R04': 'N° de Cuenta Inválida',
    'R08': 'Orden de no pagar',
    'R09': 'Día No Laborable',
    'R10': 'Falta de fondos',
    'R13': 'Sucursal inexistente',
    'R14': 'Identificación del Cliente en la Empresa Errónea',
    'R15': 'Baja del Servicio',
    'R17': 'Error de Formato',
    'R18': 'Fecha de Compensación Errónea',
    'R19': 'Importe erróneo',
    'R20': 'Moneda distinta a la de la cuenta de débito',
    'R23': 'Sucursal No Habilitada',
    'R24': 'Transacción duplicada',
    'R28': 'Rechazo primer vencimiento',
    'R29': 'Reversión ya Efectuada',
    'R31': 'Vuelta atrás de la Cámara (Unwinding)',
    'R34': 'Cliente no adherido',
    'R61': 'No existe transacción original',
    'R75': 'Fecha Inválida',
    'R86': 'Identificación de Empresa Errónea',
    'R91': 'Código de Banco incompatible con moneda',
}

def to_numeric(value):
    return int(value) if value and value.isnumeric() else 0


def eb_communication_line_map(l):
    return {
        'bank_code': to_numeric(l.partner_bank_id.bank.bcra_code
                                if l.partner_bank_id.bank else 0),
        'operation_code': 51,
        'date_due': datetime.strptime(
            l.communication_id.debit_date or
            l.invoice_id.date_due, D_FORMAT).strftime("%y%m%d"),
        'directdebit_code': l.communication_id.partner_bank_id.directdebit_code,
        'partner_id': "%05d" % l.partner_id.id,
        'currency_code': currency_code_map.get(
            l.invoice_id.currency_id.name, 'P'),
        'cbu': to_numeric(l.partner_bank_id.acc_number),
        'amount': int(l.amount * 100),
        'cuit': to_numeric(
            l.communication_id.company_id.partner_id.document_number),
        'description':
        (l.communication_id.line_description or l.invoice_id.name or ''
         ).encode('ascii', 'replace')[:10],
        'document_id': "%015x" % l.invoice_id.id,
        'response_code': '',
    }


class directdebit_communication(models.Model):
    _name = 'directdebit.communication'
    _inherit = 'directdebit.communication'

    @api.multi
    def get_type(self):
        self.ensure_one()
        if self.partner_bank_id.bank.bcra_code == '00191':
            return 'credicoop'
        return super(directdebit_communication, self).get_type()

    @api.multi
    @api.returns('directdebit.communication')
    def uri_attr(self):
        self.ensure_one()

        if not self.get_type() == 'credicoop':
            return super(directdebit_communication, self).update_context()


        return {
            'open_date_dm': datetime.strptime(
                self.open_date, DT_FORMAT).strftime("%d%m"),
            'open_date_md': datetime.strptime(
                self.open_date, DT_FORMAT).strftime("%m%d"),
            'debit_date_md': datetime.strptime(
                self.debit_date, D_FORMAT).strftime("%m%d"),
            'debit_date_dm': datetime.strptime(
                self.debit_date, D_FORMAT).strftime("%d%m"),
            'today_md': datetime.today().strftime("%m%d"),
            'today_dm': datetime.today().strftime("%d%m"),
        }

    @api.multi
    def generate_request(self):
        self.ensure_one()
        if not self.get_type() == 'credicoop':
            return super(directdebit_communication, self).generate_request()

        out = StringIO()
        for line in self.line_ids:
            ml = eb_communication_line_map(line)
            ol = eb_communication_line.format(**ml)
            out.write(ol)

        out.seek(0)
        return out

    @api.multi
    def process_response(self, response):
        self.ensure_one()
        if not self.get_type() == 'credicoop':
            return super(directdebit_communication, self).process_response(
                response)

        invoice_obj = self.env['account.invoice']

        for line in response.split('\n'):
            ml = re_be_communication_line.match(line)
            if ml:
                data = ml.groupdict()
                inv = invoice_obj.browse(int(data['document_id'], 16))
                amount = float(data['amount'])/10.
                response_code = data['response_code'].strip()

                _logger.debug("Line: %s" % line)

                if inv.state != 'open':
                    _logger.info("Invoice %s (id:%i) is not open."
                                  " Ignoring payment." % (inv.number, inv.id))
                    continue

                if response_code == '':
                    # Pay invoice
                    self.pay_invoice(inv, amount)
                    inv.message_post(body=_('Paid by Direct Debit'))
                    _logger.info("Invoice %s (id:%i) is payed."
                                  % (inv.number, inv.id))
                else:
                    # Cant pay
                    message = response_code_message.get(
                        response_code,
                        'Not recognized code %s' % response_code)
                    inv.message_post(body=_('Direct Debit ERROR: %s') % message)
                    _logger.info("Invoice %s (id:%i) ERROR: %s."
                                  % (inv.number, inv.id, message))

        return {}

directdebit_communication()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
