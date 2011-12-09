# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
#                       Raimon Esteve <resteve@zikzakmedia.com>
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
from tools.translate import _

import netsvc
import time
import mimetypes
import os
import urllib, urllib2
import binascii

from magento import *

LOGGER = netsvc.Logger()

class sale_shop(osv.osv):
    _inherit = "sale.shop"

    _columns = {
        'magento_last_export_product_templates': fields.datetime('Last Export Product Templates', help='This date is last export (Configurable products). If you need export new templates, you can modify this date (filter)'),
    }

    def magento_export_product_templates(self, cr, uid, ids, context=None):
        """
        Sync Products Templates to Magento Site filterd by magento_sale_shop
        Get ids all products templates and send one to one to Magento
        First, send all product.product (simple) and after, product.template (configurable)
        :return True
        """

        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Product Product (simple) sync")
        self.magento_export_products(cr, uid, ids, context)

        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Product Templates (configurable) sync")
        product_template_shop_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            last_exported_time = shop.magento_last_export_product_templates

            # write sale shop date last export
            self.pool.get('sale.shop').write(cr, uid, shop.id, {'magento_last_export_product_templates': time.strftime('%Y-%m-%d %H:%M:%S')})

            product_template_product_ids = self.pool.get('product.template').search(cr, uid, [('magento_exportable','=',True),('magento_configurable_sale_shop','in',shop.id)])

            for product_template in self.pool.get('product.template').perm_read(cr, uid, product_template_product_ids):
                # product.product create/modify > date exported last time
                if last_exported_time < product_template['create_date'][:19] or (product_template['write_date'] and last_exported_time < product_template['write_date'][:19]):
                    product_template_shop_ids.append(product_template['id'])

            if shop.magento_default_language:
                context['lang'] = shop.magento_default_language.code

            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Product Templates to sync: %s" % (product_template_shop_ids))

            context['shop'] = shop
            self.magento_export_product_templates_stepbystep(cr, uid, magento_app, product_template_shop_ids, context)

        return True

    def magento_export_product_templates_stepbystep(self, cr, uid, magento_app, ids, context=None):
        """
        Get all IDs product templates to create/write to Magento
        Use Base External Mapping to transform values
        Get values and call magento is step by step (product by product)
        :return mgn_id
        """

        context['magento_app'] = magento_app

        with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
            for product_template in self.pool.get('product.template').browse(cr, uid, ids, context):
                context['product_id'] = product_template.id
                values = self.pool.get('base.external.mapping').get_oerp_to_external(cr, uid, 'magento.product.configurable',[product_template.id], context)[0]

                mapping_id = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.template', product_template.id)
 
                # get dicc values
                product_sku = values['sku']
                product_type = 'configurable'
                product_attribute_set = values['set']

                # remove dicc values
                del values['id']
                del values['sku']
                del values['set']

                if mapping_id: #uptate
                    mappings = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [mapping_id])
                    product_mgn_id = mappings[0]['mgn_id']

                    store_view = None
                    if 'store_view' in context:
                        store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', context['store_view'].id)
                        store_view = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])
                        store_view = store_view[0]['mgn_id']

                    #~ print product_sku, values
                    product_api.update(product_mgn_id, values, store_view)
                    LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product SKU %s. OpenERP ID %s, Magento ID %s" % (product_sku, product_template.id, product_mgn_id))
                else: #create
                    #~ print product_type, product_attribute_set, product_sku, values
                    product_mgn_id = product_api.create(product_type, product_attribute_set, product_sku, values)
                    LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Create Product: %s. OpenERP ID %s, Magento ID %s" % (product_sku, product_template.id, product_mgn_id))
                    self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.template', product_template.id, product_mgn_id)

                # set Super Attribute Values
                
                # set product simples (update)
                
        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Products Export")

        return product_mgn_id

sale_shop()
