{
    'name': 'POS Payment - Stone Connect Terminal',
    'version': '16.0.1.0.0',
    'summary': 'Integrate POS payments with Stone Connect 2.0 terminals',
    'author': 'clebersantz, OCA',
    'license': 'AGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_payment_method_views.xml',
        'data/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_payment_stone/static/src/js/stone_pos.js',
        ],
    },
    'installable': True,
}
