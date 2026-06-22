{
    'name': 'Estate',
    'version': '1.0',
    'category': 'Real Estate/Brokerage',
    'summary': 'Real Estate Management',
    'description': 'Manage real estate properties',
    'author': 'Your Name',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}