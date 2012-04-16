# -*- encoding: utf-8 -*-
############################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Zikzakmedia S.L. (<http://www.zikzakmedia.com>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################################

from osv import fields,osv
from tools.translate import _

import pooler
import threading

class magento_sync_template_wizard(osv.osv_memory):
    _name = 'magento.sync.template.wizard'

    def _magento_sale_shop(self, cr, uid, context=None):
        ids = self.pool.get('sale.shop').search(cr, uid, [('magento_shop', '=', True)], order='id')
        shops = self.pool.get('sale.shop').read(cr, uid, ids, ['id','name'], context=context)
        return [(a['id'], a['name']) for a in shops]

    _columns = {
        'magento_sale_shop': fields.selection(_magento_sale_shop, 'Sale Shop', required=True),
        'result': fields.text('Result', readonly=True),
        'state':fields.selection([
            ('first','First'),
            ('done','Done'),
        ],'State'),
    }

    _defaults = {
        'state': lambda *a: 'first',
    }

    def sync_template(self, cr, uid, ids, data, context={}):
        """Export sync template"""

        if len(data['active_ids']) == 0:
            raise osv.except_osv(_('Error!'), _('Select templates to export'))

        form = self.browse(cr, uid, ids[0])
        shop = form.magento_sale_shop
        shop = self.pool.get('sale.shop').browse(cr, uid, shop)
        magento_app = shop.magento_website.magento_app_id

        tpl_ids = []
        for tpl in self.pool.get('product.template').browse(cr, uid, data['active_ids']):
            product_available_shops = []
            for pshop in tpl.magento_tpl_sale_shop:
                product_available_shops.append(pshop.id)

            if tpl.magento_tpl_exportable and shop.id in product_available_shops:
                tpl_ids.append(tpl.id)

        values = {
            'state':'done',
        }
        if len(tpl_ids) > 0:
            values['result'] = '%s' % (', '.join(str(x) for x in tpl_ids))
        else:
            values['result'] = _('Not available some Magento Templates to export')

        self.write(cr, uid, ids, values)

        cr.commit()

        if shop.magento_default_language:
            context['lang'] = shop.magento_default_language.code

        if len(tpl_ids) > 0:
            thread1 = threading.Thread(target=self.pool.get('sale.shop').magento_export_product_templates_stepbystep, args=(cr.dbname, uid, magento_app.id, tpl_ids, context))
            thread1.start()
        return True

magento_sync_template_wizard()
