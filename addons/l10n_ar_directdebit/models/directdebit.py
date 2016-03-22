# -*- coding: utf-8 -*-
from openerp import fields, api, models, _
from openerp.exceptions import Warning
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from urlparse import urlparse
import logging

_logger = logging.getLogger(__name__)


class directdebit_response(models.Model):
    _name = 'directdebit.response'
    _description = 'Direct debit response'

    name = fields.Char('Name')
    code = fields.Char('Code', size=3)
    description = fields.Text('Description')
    type = fields.Selection([('ok', 'No error'),
                             ('temporal', 'Temporal error'),
                             ('fatal', 'Fatal error'),
                             ('unknown', 'Unknown error')], 'Response type')
    bank_id = fields.Many2one('res.bank', 'Related error bank')


class directdebit_line(models.Model):
    _name = 'directdebit.communication.line'
    _description = 'Direct debit lines'

    @api.onchange('invoice_id')
    def invoice_id_change(self):
        bank_ids = self.invoice_id.partner_id.bank_ids.ids + [False]
        self.partner_bank_id = bank_ids[0]

    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice',
        domain="[('state','=','open'),('type','=','out_invoice')]")
    communication_id = fields.Many2one(
        'directdebit.communication',
        'Communication')
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string="Partner", readonly=True, store=False)
    partner_bank_id = fields.Many2one(
        'res.partner.bank', 'Source Bank Account',
        domain="[('partner_id','=',partner_id)]",
        context="{'default_partner_id': partner_id}")
    date_due = fields.Date(
        'Due date', size=6)
    directdebit_company_code = fields.Char(
        'Bank Company Code', size=6)
    directdebit_partner_code = fields.Char(
        'Partner Company Code', size=21)
    directdebit_currency_code = fields.Selection(
        [('P', 'Argentinian Pesos'), ('D', 'US Dollars')],
        'Currency Code')
    amount = fields.Float(
        string='Amount',
        digits=dp.get_precision('Account'),
        compute='_compute_amount',
        store=True, help="Amount to debit")
    description = fields.Char('Description', size=62)
    response_code = fields.Many2one('directdebit.response', 'Response code')

    @api.one
    @api.depends('invoice_id.amount_total', 'invoice_id.residual',
                 'communication_id.debit_residue')
    def _compute_amount(self):
        self.amount = (
            self.invoice_id.residual
            if (self.communication_id.debit_residue)
            else self.invoice_id.amount_total)


class directdebit_communication(models.Model):
    _name = 'directdebit.communication'
    _inherit = ['mail.thread']
    _description = 'Communication to recived/send from/to the bank'
    _order = "open_date desc, debit_date desc"
    _track = {
        'type': {
        },
        'state': {
            'l10n_ar_directdebit.mt_dd_communication_requested':
            lambda self, cr, uid, obj, ctx=None: obj.state == 'open',
            'l10n_ar_directdebit.mt_dd_communication_responsed':
            lambda self, cr, uid, obj, ctx=None: obj.state == 'done',
        },
    }

    @api.multi
    def _default_line_ids(self):
        context = self.env.context

        invoice_pool = self.env['account.invoice']
        r = []

        def get_partner_bank_id(inv_id):
            par = invoice_pool.browse(inv_id).partner_id
            accounts = par.bank_ids and [account.id
                                         for account in par.bank_ids
                                         if account.bank
                                         and account.bank.bcra_code
                                         and account.is_valid_cbu()]
            if accounts:
                return accounts[0]
            else:
                return False

        if context.get('invoices', False):
            invoice_ids = context.get('invoices', [])
            r = [(0, 0, {'invoice_id': inv_id,
                         'partner_bank_id': get_partner_bank_id(inv_id)})
                 for inv_id in invoice_ids]
        return r

    name = fields.Char(
        'Name',
        required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    open_date = fields.Datetime(
        'Open Date',
        default=lambda *a: datetime.now().strftime(DATETIME_FORMAT),
        readonly=True, states={'draft': [('readonly', False)]})
    debit_date = fields.Date(
        'Debit date',
        default=lambda *a: (datetime.now() + timedelta(days=3)
                            ).strftime(DATETIME_FORMAT),
        readonly=True, states={'draft': [('readonly', False)],
                               'open': [('readonly', False)]})
    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.user.company_id.id,
        required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        'Target Bank Account',
        domain="[('company_id','=',company_id)]",
        context="{'default_company_id':company_id}",
        required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    line_ids = fields.One2many(
        'directdebit.communication.line',
        'communication_id',
        'Lines',
        default=_default_line_ids,
        ondelete='cascade',
        copy=True,
        readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Open'),
         ('done', 'Done'),
         ('cancel', 'Canceled')],
        string="State",
        default='draft',
        readonly=True)
    traffic = fields.Selection(
        [('EB', 'From company to bank'),
         ('BE', 'From bank to company')],
        'Information Traffic',
        readonly=True, states={'draft': [('readonly', False)]})
    debit_residue = fields.Boolean(
        'Debit residue until total',
        default=True,
        readonly=True, states={'draft': [('readonly', False)]})
    line_description = fields.Char(
        'Concept',
        help='Concept for all lines. If not set use the invoice name.',
        size=10,
        readonly=True, states={'draft': [('readonly', False)]})
    invoice_count = fields.Integer(
        'Count of invoices',
        compute='_get_invoice_count',
        readonly=True)
    total_amount = fields.Float(
        'Total amount',
        compute='_get_total_amount',
        digits=dp.get_precision('Account'),
        readonly=True)

    @api.multi
    @api.depends('line_ids')
    def _get_invoice_count(self):
        for com in self:
            com.invoice_count = len(com.line_ids)

    @api.multi
    @api.depends('line_ids.amount')
    def _get_total_amount(self):
        for com in self:
            com.total_amount = sum(l.amount for l in com.line_ids)

    @api.multi
    def open_invoices(self):
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form,calendar,graph',
            'res_model': 'account.invoice',
            'target': 'current',
            'domain': '[("id","in",%s)]' % str(
                [i.invoice_id.id for i in self.line_ids])
        }

    @api.multi
    def get_type(self):
        return 'none'

    @api.multi
    def generate_request(self):
        return False

    @api.multi
    def process_response(self):
        return False

    @api.multi
    def do_request_by_email(self):
        raise Warning('Email request not implemented')

    @api.multi
    def do_retrieve_by_email(self):
        raise Warning('Email retrieve not implemented')

    @api.multi
    def do_request_by_ftp(self):
        """
        Send the request file to the bank ftp server.
        """
        uri = self.partner_bank_id.directdebit_request_uri.format(
            **self.uri_attr())
        if not uri:
            raise Warning('Wrong URI defined in bank')
        username = self.partner_bank_id.directdebit_username or uri.username
        password = self.partner_bank_id.directdebit_password or uri.password

        from ftplib import FTP
        import os.path as path

        o = urlparse(uri)
        _logger.info('Connecting to FTP server: %s' % o.hostname)

        ftp = FTP(o.hostname)
        if username and password:
            ftp.login(username, password)
        else:
            ftp.login()

        # Take relative directory
        workdir = path.dirname(o.path)[1:]
        filename = path.basename(o.path)
        ftp.cwd(workdir)

        _logger.info('Storing file: %s' % filename)

        data = self.generate_request()
        ftp.storbinary('STOR %s' % filename, data)
        ftp.close()

        _logger.info('Close connection.')

        return True

    @api.multi
    def do_retrieve_by_ftp(self):
        """
        Retrieve file from ftp server and process with bank protocol logic.
        """
        import urllib2

        try:
            uri = self.partner_bank_id.directdebit_response_uri.format(
                **self.uri_attr())
        except KeyError, e:
            raise Warning(_("Not exists variable '%s' to complete URI.")
                          % e.message)

        if not uri:
            raise Warning(u'Wrong URI defined in bank')

        username = self.partner_bank_id.directdebit_username
        password = self.partner_bank_id.directdebit_password

        _logger.info('Connecting to FTP server. (%s)' % uri)

        suri = uri.split('/')
        if '@' not in suri[2] and username and password:
            suri[2] = "%s:%s@%s" % (username, password, suri[2])
            uri = '/'.join(suri)

        try:
            req = urllib2.Request(uri)
            res = urllib2.urlopen(req)
            data = res.read()
        except urllib2.URLError, e:
            raise Warning(_("Retrieve Error.\n%s") % e.reason)

        _logger.info('Processing file.')
        self.process_response(data)

        _logger.info('Close connection.')
        res.close()
        return True

    @api.multi
    def uri_attr(self):
        """
        Return dict to complete the URI by variables.
        Each variable depends on bank protocol.
        """
        return {
            'username': self.directdebit_username,
            'password': self.directdebit_password,
        }

    @api.multi
    def do_request(self):
        """
        Do request.
        """
        self.ensure_one()
        if self.state != 'draft':
            return False

        if self.open_date and fields.Datetime.now() < self.open_date:
            return False

        self.validate()

        self.open_date = fields.Datetime.now()

        if self.partner_bank_id.directdebit_request_uri:
            o = urlparse(self.partner_bank_id.directdebit_request_uri)
            if o.scheme:
                request = getattr(self,
                                  'do_request_by_%s' % o.scheme,
                                  False)
                if not request:
                    raise Warning('Scheme processor do not implemented.'
                                  ' Check your URI in the account bank'
                                  ' configuration to use any valid.')
                request()

        self.state = 'open'
        return True

    @api.multi
    def do_pool(self):
        """
        Take URI.
        """
        self.ensure_one()
        if self.partner_bank_id.directdebit_response_uri:
            o = urlparse(self.partner_bank_id.directdebit_response_uri)
            if o.scheme:
                retrieve = getattr(self,
                                   'do_retrieve_by_%s' % o.scheme,
                                   False)
                if not retrieve:
                    raise Warning('Scheme processor do not implemented.'
                                  ' Check your URI in the account bank'
                                  ' configuration to use any valid.')
                retrieve()

        self.write({'state': 'done'})
        pass

    @api.multi
    def do_cancel(self):
        self.write({'state': 'cancel'})
        pass

    @api.multi
    def do_todraft(self):
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True

    @api.multi
    def _validate_date(self):
        self.ensure_one()
        if not (datetime.strptime(self.debit_date, DATE_FORMAT) -
                datetime.now()).days >= 2:
            raise Warning(
                _("Error\nDebit date must be 3 days more than today."))

    @api.multi
    def _validate_bank(self):
        self.ensure_one()

        if not self.partner_bank_id.bank.bcra_code:
            raise Warning(
                _("Error\n"
                    "Your Target Bank Account has not BCRA code assigned.\n"
                    "Check the "
                    "<a href='http://www.bcra.gob.ar/sisfin/sf020101.asp"
                    "?bco=AAA20&tipo=3'>value</a>"
                    " and setup before continue."))
        if self.get_type() == 'none':
            raise Warning("Can't identify bank logic.")
        if not self.partner_bank_id.directdebit_request_uri:
            raise Warning('No URI definition to send data to the bank.')
        if not self.partner_bank_id.directdebit_response_uri:
            raise Warning('No URI definition to receive data from the bank.')
        if not self.partner_bank_id.directdebit_code:
            raise Warning(
                _("Error\n"
                    "Your Target Bank Account has not a direct debit"
                    " code assigned.\n"
                    "Please ask to your bank to setup before continue."))

    @api.multi
    def _validate_lines(self):
        self.ensure_one()
        for line in self.line_ids:
            if not line.invoice_id.state == "open":
                raise Warning(
                    _("Error\nInvoice %s is not Open.\n"
                        "Please, select an Open Invoice or Validate"
                        " before continue.") % line.invoice_id.number)
            if not line.partner_bank_id:
                raise Warning(
                    _("Error\nNo bank account assigned to %s.\n"
                        "Setup before continue.") % line.invoice_id.number)
            if not line.partner_bank_id.bank:
                raise Warning(
                    _("Error\nNo bank assigned to the bank account for %s."
                        "\nSetup before continue.") % line.invoice_id.number)
            if not line.partner_bank_id.bank.bcra_code:
                raise Warning(
                    _("Error\nThe bank associated to the line %s has not"
                        " BCRA code assigned.\nCheck the value for %s in"
                        " the BCRA and setup before continue.")
                    % (line.partner_bank_id.bank.name,
                        line.invoice_id.number))
            if not (line.partner_bank_id.acc_number and
                    line.partner_bank_id.is_valid_cbu()):
                raise Warning(
                    _("Error\n"
                        "The bank account associated to %s is not a valid"
                        " CBU.\nCheck it or ask to your partner and setup"
                        " before continue.") % line.invoice_id.number)

    @api.multi
    def pay_invoice(self, inv, amount):
        """
        Automatic payment of invoice using account.voucher.
        """
        self.ensure_one()
        voucher_obj = self.env['account.voucher']
        bnk_journal = self.partner_bank_id.journal_id
        voucher = voucher_obj.with_context(
            payment_expected_currency=inv.currency_id.id,
            default_partner_id=(
                self.env['res.partner']._find_accounting_partner(
                    inv.partner_id).id),
            default_amount=(inv.type in ('out_refund', 'in_refund') and -amount
                            or amount),
            default_reference=inv.name or inv.number,
            close_after_process=True,
            invoice_type=inv.type,
            invoice_id=inv.id,
            default_type=(inv.type in ('out_invoice',
                                       'out_refund') and 'receipt'
                          or 'payment'),
            type=(inv.type in ('out_invoice', 'out_refund') and 'receipt'
                  or 'payment'),
            default_journal_id=bnk_journal.id,
            default_account_id=
            bnk_journal.default_debit_account_id.id
        ).create({
        })
        update = voucher.recompute_voucher_lines(
            voucher.partner_id.id,
            voucher.journal_id.id,
            voucher.amount,
            voucher.currency_id.id,
            voucher.type,
            voucher.date
        )
        values = update['value']
        values['line_cr_ids'] = [(0, 0, v)
                                 for v in values['line_cr_ids']]
        values['line_dr_ids'] = [(0, 0, v)
                                 for v in values['line_dr_ids']]
        voucher.write(values)
        voucher.compute_tax()
        voucher.signal_workflow('proforma_voucher')
        return True

    @api.multi
    def validate(self):
        for com in self:
            com._validate_date()
            com._validate_bank()
            com._validate_lines()

        return True

    @api.multi
    def process(self):
        """
        For all open communication try to download and close it.
        """
        for com in self.search([('state', '=', 'open')]):
            try:
                com.do_pool()
            except Warning, e:
                self.message_post(
                    subject=_('Error closing %s.') % com.name,
                    body='%s.' % str(e),
                    type='notification',
                    subtype='mt_comment'
                )
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
