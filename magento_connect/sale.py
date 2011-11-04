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

from magento import *

import netsvc
import time

class sale_shop(osv.osv):
    _inherit = "sale.shop"

    _columns = {
        'magento_shop': fields.boolean('Magento Shop', readonly=True),
        'magento_website': fields.many2one('magento.website', 'Magento Website'),
        'magento_scheduler': fields.boolean('Scheduler', help='Available this Sale Shop crons (import/export)'),
        'magento_tax_include': fields.boolean('Tax Include'),
        'magento_payment_types': fields.one2many('magento.sale.shop.payment.type', 'shop_id', 'Payment Type'),
        'magento_default_language': fields.many2one('res.lang', 'Language Default', help='Default language this shop. If not select, use lang user'),
        'magento_sale_price': fields.selection([('saleprice','Sale Price'),('pricelist','Pricelist')], 'Price'),
        'magento_sale_stock': fields.selection([('realstock','Real Stock'),('virtualstock','Virtual Stock')], 'Stock'),
        'magento_last_export_products': fields.datetime('Last Export Products', help='This date is last export. If you need export new products, you can modify this date (filter)'),
        'magento_last_export_prices': fields.datetime('Last Export Prices', help='This date is last export. If you need export all product prices, empty this field (long sync)'),
        'magento_last_export_stock': fields.datetime('Last Export Stock', help='This date is last export. If you need export all product prices, empty this field (long sync)'),
        'magento_last_export_images': fields.datetime('Last Export Image', help='This date correspond to the last export. If you need export all images, left empty this field.'),
    }

    _defaults = {
        'magento_sale_price': 'saleprice',
        'magento_sale_stock': 'virtualstock',
    }

    def magento_export_products(self, cr, uid, ids, context=None):
        """
        Sync Products to Magento Site filterd by magento_sale_shop
        Get ids all products and send one to one to Magento
        :return True
        """

        logger = netsvc.Logger()

        product_shop_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            last_exported_time = shop.magento_last_export_products

            product_product_ids = self.pool.get('product.product').search(cr, uid, [('magento_exportable','=',True),('magento_sale_shop','in',shop.id)])

            for product_product in self.pool.get('product.product').perm_read(cr, uid, product_product_ids):
                # product.product create/modify > date exported last time
                if last_exported_time < product_product['create_date'][:19] or (product_product['write_date'] and last_exported_time < product_product['write_date'][:19]):
                    product_shop_ids.append(product_product['id'])

            if shop.magento_default_language:
                context['lang'] = shop.magento_default_language.code

            logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Products to sync: %s" % (product_shop_ids))

            context['shop'] = shop
            self.magento_export_products_stepbystep(cr, uid, magento_app, product_shop_ids, context)

        return True

    def magento_export_products_stepbystep(self, cr, uid, magento_app, ids, context=None):
        """
        Get all IDs products to create/write to Magento
        Use Base External Mapping to transform values
        Get values and call magento is step by step (product by product)
        :return mgn_id
        """

        logger = netsvc.Logger()

        context['magento_app'] = magento_app

        with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
            for product in self.pool.get('product.product').browse(cr, uid, ids, context):
                context['product_id'] = product.id
                product_product_vals = self.pool.get('base.external.mapping').get_oerp_to_external(cr, uid, 'magento.product.product',[product.id], context)
                product_template_vals = self.pool.get('base.external.mapping').get_oerp_to_external(cr, uid, 'magento.product.template',[product.product_tmpl_id.id], context)

                values = dict(product_product_vals[0], **product_template_vals[0])

                mgn_id = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.product', product.id)

                # get dicc values
                product_sku = values['sku']
                product_type = values['type']
                product_attribute_set = values['set']

                # remove dicc values
                del values['id']
                del values['sku']
                del values['type']
                del values['set']

                if mgn_id: #uptate
                    store_view = None
                    if 'store_view' in context:
                        store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', context['store_view'].id)
                        store_view = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])
                        store_view = store_view[0]['mgn_id']

                    #~ print product_sku, values
                    product_api.update(product_sku, values, store_view)
                    logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product SKU %s. OpenERP ID %s, Magento ID %s" % (product_sku, product.id, mgn_id))
                else: #create
                    #~ print product_type, product_attribute_set, product_sku, values
                    mgn_id = product_api.create(product_type, product_attribute_set, product_sku, values)
                    logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Create Product: %s. OpenERP ID %s, Magento ID %s" % (product_sku, product.id, product_mgn_id))
                    self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.product', product.id, product_mgn_id)

        logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Products Export")

        # write sale shop date last export
        self.pool.get('sale.shop').write(cr, uid, [context['shop'].id], {'magento_last_export_products': time.strftime('%Y-%m-%d %H:%M:%S')})

        return mgn_id

    def magento_export_prices(self, cr, uid, ids, context=None):
        """
        Sync Products Price to Magento Site
        Get price products when last export time and send one to one to Magento
        :return True
        """

        logger = netsvc.Logger()

        decimal = self.pool.get('decimal.precision').precision_get(cr, uid, 'Sale Price')

        product_shop_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            last_exported_time = shop.magento_last_export_prices

            product_product_ids = self.pool.get('product.product').search(cr, uid, [('magento_exportable','=',True),('magento_sale_shop','in',shop.id)])

            for product_product in self.pool.get('product.product').perm_read(cr, uid, product_product_ids):
                # product.product create/modify > date exported last time
                if last_exported_time < product_product['create_date'][:19] or (product_product['write_date'] and last_exported_time < product_product['write_date'][:19]):
                    product_shop_ids.append(product_product['id'])

            with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
                context['shop'] = shop
                for product in self.pool.get('product.product').browse(cr, uid, product_shop_ids, context):
                    mgn_id = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.product', product.id)
                    if mgn_id:
                        mgn_id = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [mgn_id])[0]['mgn_id']
                    store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', shop.id)
                    store_view  = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])[0]['mgn_id']

                    price = ''
                    if not mgn_id:#not product created/exist in Magento. Create
                        mgn_id = self.magento_export_products_stepbystep(cr, uid, magento_app, ids, context)

                    if shop.magento_sale_price == 'pricelist' and shop.pricelist_id:
                        price = self.pool.get('product.pricelist').price_get(cr, uid, [shop.pricelist_id.id], product.id, 1.0)[shop.pricelist_id.id]
                    else:
                        price = product.product_tmpl_id.list_price

                    if shop.magento_tax_include:
                        price_compute_all = self.pool.get('account.tax').compute_all(cr, uid, product.product_tmpl_id.taxes_id, price, 1, address_id=None, product=product.product_tmpl_id, partner=None)
                        price = price_compute_all['total_included']

                    if price:
                        price = '%.*f' % (decimal, price) #decimal precision

                    data = {'price':price}
                    product_mgn_id = product_api.update(mgn_id, data, store_view)

                    logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product Prices: %s. OpenERP ID %s, Magento ID %s" % (price, product.id, mgn_id))

            self.write(cr, uid, [context['shop'].id], {'magento_last_export_prices': time.strftime('%Y-%m-%d %H:%M:%S')})

        logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Product Prices Export")

        return True

    def magento_export_stock(self, cr, uid, ids, context=None):
        """
        Sync Products Stock to Magento Site
        Get stock all products and send one to one to Magento
        :return True
        """

        logger = netsvc.Logger()

        product_shop_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            stock_id = shop.warehouse_id.lot_stock_id.id

            product_shop_ids = self.pool.get('product.product').search(cr, uid, [('magento_exportable','=',True),('magento_sale_shop','in',shop.id)])

            # base_sale_multichannels
            if shop.magento_last_export_stock:
                recent_move_ids = self.pool.get('stock.move').search(cr, uid, [('write_date', '>', shop.magento_last_export_stock),('product_id', 'in', product_shop_ids),('state', '!=', 'draft'),('state', '!=', 'cancel')])
            else:
                recent_move_ids = self.pool.get('stock.move').search(cr, uid, [('product_id', 'in', product_shop_ids),('state', '!=', 'draft'),('state', '!=', 'cancel')])
            product_ids = [move.product_id.id for move in self.pool.get('stock.move').browse(cr, uid, recent_move_ids) if move.product_id.state != 'obsolete']
            product_ids = [x for x in set(product_ids)]

            with Inventory(magento_app.uri, magento_app.username, magento_app.password) as inventory_api:
                context['shop'] = shop
                for product in self.pool.get('product.product').browse(cr, uid, product_ids, context):
                    stock = 0
                    mgn_id = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.product', product.id)
                    if mgn_id:
                        mgn_id = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [mgn_id])[0]['mgn_id']

                    if not mgn_id:#not product created/exist in Magento. Create
                        mgn_id = self.magento_export_products_stepbystep(cr, uid, magento_app, ids, context)

                    """Calculate Stock from real stock or virtual Stock"""
                    if shop.magento_sale_price == 'realstock':
                        stock = self.pool.get('product.product').read(cr, uid, product.id, ['qty_available'], {'location': stock_id})['qty_available']
                    else:
                        stock = self.pool.get('product.product').read(cr, uid, product.id, ['virtual_available'], {'location': stock_id})['virtual_available']

                    """Is in Stock"""
                    is_in_stock = int(stock > 0) or False

                    data = {'qty':stock, 'is_in_stock':is_in_stock}
                    inventory_api.update(mgn_id, data)

                    logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Update Product Stock: %s. OpenERP ID %s, Magento ID %s" % (stock, product.id, mgn_id))

            self.write(cr, uid, [context['shop'].id], {'magento_last_export_stock': time.strftime('%Y-%m-%d %H:%M:%S')})

        logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Product Stock Export")

        return True


    #TODO EXPORT IMAGES
    def magento_export_images(self, cr, uid, ids, context=None):
        """
        Sync Images to Magento Site filterd by magento_sale_shop
        Get ids all products and send one to one to Magento
        :return True
        """

        print self
        print ids
        print context

        logger = netsvc.Logger()

        magento_external_referential_obj = self.pool.get('magento.external.referential')
        product_product_obj = self.pool.get('product.product')

        magento_product_images_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            last_exported_time = shop.magento_last_export_images
            print "-----------------------------------------"
            print "last_exported_time: ", last_exported_time

            product_images_ids = self.pool.get('product.image.magento.app').search(cr, uid, [('magento_app_id','=',magento_app.id)])

            for product_product in self.pool.get('product.images').perm_read(cr, uid, product_images_ids):
                # product.product create/modify > date exported last time
                if last_exported_time < product_product['create_date'][:19] or (product_product['write_date'] and last_exported_time < product_product['write_date'][:19]):
                    magento_product_images_ids.append(product_product['id'])

            if len(magento_product_images_ids) > 0:
                magento_product_images_ids = product_images_ids

            print "=======TEST2========"
            print magento_product_images_ids
            with ProductImages(magento_app.uri, magento_app.username, magento_app.password) as product_image_api:
                for product_image in self.pool.get('product.images').browse(cr, uid, magento_product_images_ids):
                    print "====product image==="
                    print product_image


#
            #magento_external_referential_ids = magento_external_referential_obj.search(cr, uid, [
                #('model_id.model', '=', 'product.product'),
                #('magento_app_id', '=', shop.magento_website.id),
                #('oerp_id', 'in', product_product_ids),
            #], context = context)
            #magento_product_ids = magento_external_referential_obj.read(cr, uid, magento_external_referential_ids, ['oerp_id', 'mgn_id'], context)
            #print "Productes mapejats: ", magento_product_ids
#
            #product_ids = []
            #map_product = {}
            #for magento_product_id in magento_product_ids:
                #if magento_product_id['oerp_id'] in product_product_ids:
                    #product_ids.append(magento_product_id['oerp_id'])
                    #map_product[magento_product_id['oerp_id']] = magento_product_id['mgn_id']
            #print "productes a mapejar: ", product_ids
#
            #for product in product_product_obj.browse(cr, uid, product_ids, context):
                #print 'product: ', product
                #print 'magento product', map_product[product.id]
                #for image in product.image_ids:
                    #print 'image: ', image
                #with ProductImages(magento_app.uri, magento_app.username, magento_app.password) as product_image_api:
                    #try:
                        #product_images = product_image_api.list(map_product[product.id])
                        #for product_image in product_images:
                            #product_image = product_image_api.info(map_product[product.id], product_images['file'])
                            #print "product_image: ", product_image
                    #except:
                        #logger.notifyChannel('Magento Sale Shop', netsvc.LOG_ERROR, "Products %s not found" % (map_product[product.id]))













#
            #
            #product_product_ids = self.pool.get('product.product').search(cr, uid, [('magento_exportable','=',True), ('magento_sale_shop','in',shop.id)])
#
            #for product_product in self.pool.get('product.product').perm_read(cr, uid, product_product_ids):
                 ####product.product create/modify > date exported last time
                #if last_exported_time < product_product['create_date'][:19] or (product_product['write_date'] and last_exported_time < product_product['write_date'][:19]):
                    #product_shop_ids.append(product_product['id'])
#
            #if shop.magento_default_language:
                #context['lang'] = shop.magento_default_language.code
#
            #logger.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Products to sync: %s" % (product_shop_ids))
#
            #context['shop'] = shop
            #self.magento_export_products_stepbystep(cr, uid, magento_app, product_shop_ids, context)

        return True

    def _sale_shop(self, cr, uid, callback, context=None):
        """
        Sale Shop Magento available Scheduler
        :return True
        """
        if context is None:
            context = {}

        ids = self.pool.get('sale.shop').search(cr, uid, [('magento_shop', '=', True), ('magento_scheduler', '=', True)], context=context)
        if ids:
            callback(cr, uid, ids, context=context)

        return True

    def run_export_catalog_scheduler(self, cr, uid, context=None):
        """Scheduler Catalog Product Cron"""
        self._sale_shop(cr, uid, self.magento_export_products, context=context)

    def run_export_price_scheduler(self, cr, uid, context=None):
        """Scheduler Catalog Price Cron"""
        self._sale_shop(cr, uid, self.magento_export_prices, context=context)

    def run_export_stock_scheduler(self, cr, uid, context=None):
        """Scheduler Catalog Stock Cron"""
        self._sale_shop(cr, uid, self.magento_export_stock, context=context)

sale_shop()

class magento_sale_shop_payment_type(osv.osv):
    _name = "magento.sale.shop.payment.type"

    _description = "Magento Sale Shop Payment Type"
    _rec_name = "payment_type_id"

    _columns = {
        'payment_type_id': fields.many2one('payment.type','Payment Type', required=True),
        'shop_id': fields.many2one('sale.shop','Shop', required=True),
        'picking_policy': fields.selection([('direct', 'Partial Delivery'), ('one', 'Complete Delivery')], 'Packing Policy'),
        'order_policy': fields.selection([
         ('prepaid', 'Payment Before Delivery'),
         ('manual', 'Shipping & Manual Invoice'),
         ('postpaid', 'Invoice on Order After Delivery'),
         ('picking', 'Invoice from the Packing'),
        ], 'Shipping Policy'),
        'invoice_quantity': fields.selection([('order', 'Ordered Quantities'), ('procurement', 'Shipped Quantities')], 'Invoice on'),
        'app_payment': fields.char('App Payment', size=255, required=True, help='Name App Payment module (example, paypal, servired, cash_on_delivery,...'),
     }

magento_sale_shop_payment_type()
