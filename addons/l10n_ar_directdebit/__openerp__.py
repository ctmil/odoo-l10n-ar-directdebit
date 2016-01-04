# -*- coding: utf-8 -*-
{
    'name': 'Direct Debit',
    'version': '8.0.1',
    'category': 'Sale',
    'description': 'Direct Debit support for Agentinian Banks',
    'author': 'Moldeo Interactive',
    'website': 'http://biz.moldeo.coop/',
    'images':  [],
    'depends': [
        'base',
        'account',
        'l10n_ar_bank',
        'l10n_ar_invoice',
    ],
    'demo': [],
    'data': [
        'data/bank_view.xml',
        'data/directdebit_view.xml',
        'wizard/generate_communication_view.xml',
        'security/direct_debit_security.xml',
        'security/ir.model.access.csv',
    ],
    'test': [
        'test/products.yml',
        'test/partners.yml',
        'test/com_ri1.yml',
        'test/com_ri2.yml',
        'test/inv_ri2ri.yml',
        'test/inv_ri2rm.yml',
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
