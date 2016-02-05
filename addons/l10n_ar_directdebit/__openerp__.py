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
    'demo': [
        'data/demo_bankaccount.yml',
    ],
    'data': [
        'data/directdebit_data.xml',
        'views/bank_view.xml',
        'views/directdebit_view.xml',
        'views/generate_communication_view.xml',
        'security/direct_debit_security.xml',
        'security/ir.model.access.csv',
    ],
    'test': [
        # 'test/generate_communication_wizard.yml',
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
