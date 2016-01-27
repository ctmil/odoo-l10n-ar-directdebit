# -*- coding: utf-8 -*-
{
    'name': 'Direct Debit',
    'version': '8.0.2',
    'category': 'Sale',
    'description': 'Direct Debit support for Agentinian Banks',
    'author': 'Moldeo Interactive',
    'website': 'http://biz.moldeo.coop/',
    'images':  [],
    'depends': [
        'base',
        'account',
        'l10n_ar_bank',
    ],
    'demo':    [],
    'data':    [
        'data/bank_view.xml',
        'data/directdebit_view.xml',
        'data/directdebit_data.xml',
        'wizard/generate_communication_view.xml',
        'security/direct_debit_security.xml',
        'security/ir.model.access.csv',
    ],
    'test':    [
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
