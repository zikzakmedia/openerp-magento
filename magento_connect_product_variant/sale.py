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
import pooler
import threading

from magento import *

LOGGER = netsvc.Logger()

class sale_shop(osv.osv):
    _inherit = "sale.shop"

    _columns = {
        'magento_last_export_product_templates': fields.datetime('Last Export Product Templates', help='This date is last export (Configurable products). If you need export new templates, you can modify this date (filter)'),
        'magento_last_export_prices_templates': fields.datetime('Last Export Prices Templates', help='This date is last export. If you need export all product templates prices, empty this field (long sync)'),
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

            product_template_product_ids = self.pool.get('product.template').search(cr, uid, [('magento_tpl_exportable','=',True),('magento_tpl_sale_shop','in',shop.id)])

            for product_template in self.pool.get('product.template').perm_read(cr, uid, product_template_product_ids):
                # product.product create/modify > date exported last time
                if last_exported_time < product_template['create_date'][:19] or (product_template['write_date'] and last_exported_time < product_template['write_date'][:19]):
                    product_template_shop_ids.append(product_template['id'])

            if shop.magento_default_language:
                context['lang'] = shop.magento_default_language.code

            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Product Templates to sync: %s" % (product_template_shop_ids))

            context['shop'] = shop

            cr.commit()
            thread1 = threading.Thread(target=self.magento_export_product_templates_stepbystep, args=(cr.dbname, uid, magento_app.id, product_template_shop_ids, context))
            thread1.start()

        return True

    def magento_export_product_templates_stepbystep(self, db_name, uid, magentoapp, ids, context=None):
        """
        Get all IDs product templates to create/write to Magento
        Use Base External Mapping to transform values
        Get values and call magento is step by step (product by product)
        :return mgn_ids
        """

        if len(ids) == 0:
            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Product Templates Export")
            return True

        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()

        magento_app = self.pool.get('magento.app').browse(cr, uid, magentoapp)

        context['magento_app'] = magento_app
        magento_external_referential = self.pool.get('magento.external.referential')

        product_mgn_ids = []
        attributes = {}

        with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
            for product_template in self.pool.get('product.template').browse(cr, uid, ids, context):
                product_template_id = product_template.id
                context['product_id'] = product_template_id
                values = self.pool.get('base.external.mapping').get_oerp_to_external(cr, uid, 'magento.product.configurable',[product_template_id], context)[0]

                mapping_id = magento_external_referential.check_oerp2mgn(cr, uid, magento_app, 'product.template', product_template_id)

                # get dicc values
                product_sku = values['sku']
                product_type = 'configurable'
                product_attribute_set = values['set']

                # remove dicc values
                del values['id']
                del values['sku']
                del values['set']

                if mapping_id: #uptate
                    mappings = magento_external_referential.get_external_referential(cr, uid, [mapping_id])
                    product_mgn_id = mappings[0]['mgn_id']

                    store_view = None
                    if 'store_view' in context:
                        store_view = magento_external_referential.check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', context['store_view'].id)
                        store_view = magento_external_referential.get_external_referential(cr, uid, [store_view])
                        store_view = store_view[0]['mgn_id']

                    #~ print product_sku, values
                    product_api.update(product_mgn_id, values, store_view)
                    LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product SKU %s. OpenERP ID %s, Magento ID %s" % (product_sku, product_template_id, product_mgn_id))
                else: #create
                    try:
                        product_mgn_id = product_api.create(product_type, product_attribute_set, product_sku, values)
                        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Create Product: %s. OpenERP ID %s, Magento ID %s" % (product_sku, product_template_id, product_mgn_id))
                        magento_external_referential.create_external_referential(cr, uid, magento_app, 'product.template', product_template_id, product_mgn_id)
                    except:
                        product_mgn_id = False
                        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_ERROR, "Magento Create Product Template: %s %s." % (product_sku, product_template.id))

                if product_mgn_id:
                    with ProductConfigurable(magento_app.uri, magento_app.username, magento_app.password) as productconfigurable_api:
                        # set Super Attribute Values
                        for dimension_type_id in product_template.dimension_type_ids:
                            dimension_mapping = magento_external_referential.check_oerp2mgn(cr, uid, magento_app, 'product.variant.dimension.type', dimension_type_id)
                            if dimension_mapping:
                                mappings = magento_external_referential.get_external_referential(cr, uid, [dimension_mapping])
                                attribute_mgn_id = mappings[0]['mgn_id']
                                if attribute_mgn_id:
                                    product = productconfigurable_api.setSuperAttributeValues(product_mgn_id, attribute_mgn_id)

                        # set product simples (update)
                        products = []
                        for product_id in self.pool.get('product.product').search(cr, uid, [('product_tmpl_id','=',product_template_id)]):
                            product_mapping = magento_external_referential.check_oerp2mgn(cr, uid, magento_app, 'product.product', product_id)
                            if product_mapping:
                                mappings = magento_external_referential.get_external_referential(cr, uid, [product_mapping])
                                product_mgn = mappings[0]['mgn_id']
                                products.append(product_mgn)
                        if len(products)>0:
                            try:
                                product = productconfigurable_api.update(product_mgn_id, products, attributes)
                                LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product Configurable %s. OpenERP ID %s, Magento ID %s" % (product_sku, product_template_id, product_mgn_id))
                            except:
                                LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_ERROR, "Error Product Configurable: Magento product ID %s, Products ID %s" % (product_mgn_id, products))
                    # return []
                    product_mgn_ids.append(product_mgn_id)

                cr.commit()

        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Products Export")

        return product_mgn_ids

    def magento_export_prices_templates(self, cr, uid, ids, context=None):
        """
        Sync Products Templates Price to Magento Site
        Get price product.template when last export time and send one to one to Magento
        :return True
        """


        product_shop_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            last_exported_time = shop.magento_last_export_prices_templates

            # write sale shop date last export
            self.write(cr, uid, shop.id, {'magento_last_export_prices_templates': time.strftime('%Y-%m-%d %H:%M:%S')})

            product_template_ids = self.pool.get('product.template').search(cr, uid, [('magento_tpl_exportable','=',True),('magento_tpl_sale_shop','in',shop.id)])

            for product_template in self.pool.get('product.template').perm_read(cr, uid, product_template_ids):
                # product.product create/modify > date exported last time
                if last_exported_time < product_template['create_date'][:19] or (product_template['write_date'] and last_exported_time < product_template['write_date'][:19]):
                    product_shop_ids.append(product_template['id'])

            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Products Price to sync: %s" % (product_shop_ids))

            cr.commit()
            thread1 = threading.Thread(target=self.magento_export_prices_templates_stepbystep, args=(cr.dbname, uid, magento_app.id, shop.id, product_shop_ids, context))
            thread1.start()

        return True

    def magento_export_prices_templates_stepbystep(self, db_name, uid, magentoapp, saleshop, ids, context=None):
        """
        Get all IDs products to update Prices in Magento
        :param dbname: str
        :magentoapp: int
        :saleshop: int
        :ids: list
        :return mgn_id
        """

        if len(ids) == 0:
            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Product Templates Prices Export")
            return True

        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()

        decimal = self.pool.get('decimal.precision').precision_get(cr, uid, 'Sale Price')
        magento_external_referential_obj = self.pool.get('magento.external.referential')

        magento_app = self.pool.get('magento.app').browse(cr, uid, magentoapp)
        context['magento_app'] = magento_app

        shop = self.pool.get('sale.shop').browse(cr, uid, saleshop)
        context['shop'] = shop

        decimal = self.pool.get('decimal.precision').precision_get(cr, uid, 'Sale Price')

        with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
            for product in self.pool.get('product.template').browse(cr, uid, ids, context):
                LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Waiting OpenERP ID %s...." % (product.id))
                mgn_id = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.template', product.id)
                if mgn_id:
                    mgn_id = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [mgn_id])[0]['mgn_id']
                #~ store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', shop.id)
                #~ store_view  = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])[0]['mgn_id']

                price = ''
                if not mgn_id:#not product created/exist in Magento. Create
                    LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Force create product ID %s" % (product.id))
                    mgn_id = self.magento_export_product_templates_stepbystep(cr.dbname, uid, magento_app.id, [product.id], context)

                if shop.magento_sale_price == 'pricelist' and shop.pricelist_id:
                    price = self.pool.get('product.pricelist').price_get(cr, uid, [shop.pricelist_id.id], product.id, 1.0)[shop.pricelist_id.id]
                else:
                    price = product.list_price

                if shop.magento_tax_include:
                    price_compute_all = self.pool.get('account.tax').compute_all(cr, uid, product.taxes_id, price, 1, address_id=None, product=product, partner=None)
                    price = price_compute_all['total_included']

                if price:
                    price = '%.*f' % (decimal, price) #decimal precision

                data = {'price':price}
                #~ product_mgn_id = product_api.update(mgn_id, data, store_view)
                product_mgn_id = product_api.update(mgn_id, data)

                LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product Template Prices: %s. OpenERP ID %s, Magento ID %s" % (price, product.id, mgn_id))

        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Product Template Prices Export")

        return True

    def run_export_catalog_configurable_scheduler(self, cr, uid, context=None):
        """Scheduler Catalog Product Configurables Cron"""
        self._sale_shop(cr, uid, self.magento_export_product_templates, context=context)

sale_shop()
