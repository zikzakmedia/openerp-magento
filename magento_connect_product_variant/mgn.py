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
import pooler
import threading
import time

LOGGER = netsvc.Logger()

class magento_app(osv.osv):
    _inherit = 'magento.app'

    def core_sync_attributes_dimension_type(self, cr, uid, ids, context):
        """
        def sync Attributes Magento to Product variant dimension type
        Only create new values if not exist; not update or delete
        :ids list magento app
        :return True
        """

        for magento_app in self.browse(cr, uid, ids):
            with ProductAttributeSet(magento_app.uri, magento_app.username, magento_app.password) as product_attribute_set_api:
                product_attribute_sets = product_attribute_set_api.list()

            with ProductAttribute(magento_app.uri, magento_app.username, magento_app.password) as product_attribute_api:
                product_variant_dimension_type = {} #{'key':'value'}
                product_variant_dimension_options = {} #{'key':'[options]'}
                for product_attribute_set in product_attribute_sets:
                    product_attributes = product_attribute_api.list(product_attribute_set['set_id'])
                    for product_attribute in product_attributes:
                        attribute = product_attribute_api.info(product_attribute['attribute_id'])

                        if not isinstance(attribute, dict):
                            LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Atribute dicc blank! %s" % (product_attribute['attribute_id']))
                            continue

                        is_global = attribute.get('is_global',False)
                        if not is_global:
                            LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Error get attribute values! %s" % (product_attribute['attribute_id']))
                            continue

                        if(int(attribute['is_global']) == 1 and int(attribute['is_configurable']) == 1 and attribute['frontend_input'] == 'select'):
                            # print "Attribut Configurable %s"  % attribute['frontend_label']
                            attribute_options = product_attribute_api.options(attribute['attribute_code'])
                            product_variant_dimension_type[attribute['attribute_code']] = attribute['attribute_id']
                            product_variant_dimension_options[attribute['attribute_code']] = attribute_options

            for type_name, dimension_options in product_variant_dimension_options.iteritems():
                magento_id = product_variant_dimension_type[type_name]
                dimension_id = self.pool.get('product.variant.dimension.type').magento_dimension_type(cr, uid, magento_app, type_name, magento_id)
                self.pool.get('product.variant.dimension.option').magento_dimension_option(cr, uid, magento_app, dimension_id, dimension_options)

            LOGGER.notifyChannel('Magento Import Dimensions', netsvc.LOG_INFO, "End import dimensions magento %s." % (magento_app.name))
        return True

    def core_sync_products(self, cr, uid, ids, context):
        """
        def sync Product Product Magento to OpenERP
        Only create new values if not exist; not update or delete
        :ids list
        :return True
        """

        product_obj = self.pool.get('product.product')

        for magento_app in self.browse(cr, uid, ids):
            if not magento_app.magento_default_storeview:
                raise osv.except_osv(_("Alert"), _("Select Store View Magento"))

            with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
                if 'ofilter' in context:
                    ofilter = context['ofilter']
                    ofilter2 = False
                else:
                    ofilter = {
                        'created_at':{'from':magento_app.from_import_products, 'to':magento_app.to_import_products},
                    }
                    ofilter2 = {
                        'updated_at':{'from':magento_app.from_import_products, 'to':magento_app.to_import_products},
                    }

                store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', magento_app.magento_default_storeview.id)
                store_view = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])
                store_view = store_view[0]['mgn_id']

                #~ Update date last import
                date_from_import = magento_app.to_import_products and magento_app.to_import_products or time.strftime('%Y-%m-%d %H:%M:%S')
                self.write(cr, uid, ids, {'from_import_products': date_from_import})
                self.write(cr, uid, ids, {'to_import_products': time.strftime('%Y-%m-%d %H:%M:%S')})

                products = product_api.list(ofilter, store_view)
                LOGGER.notifyChannel('Magento App', netsvc.LOG_INFO, "Filter %s" % (ofilter))

                if ofilter2:
                    products = products+product_api.list(ofilter2, store_view)
                    LOGGER.notifyChannel('Magento App', netsvc.LOG_INFO, "Filter %s" % (ofilter2))

                LOGGER.notifyChannel('Magento App', netsvc.LOG_INFO, "Start Sync Products magento app %s." % (magento_app.name))
                self.pool.get('magento.log').create_log(cr, uid, magento_app, 'product.product', 0, '', 'done', _('Start Import/Update products: %s') % ofilter )

                # remove same items in list
                prods = []
                for prod in products:
                    product_id = prod['product_id']
                    add = True
                    for p in prods:
                        if product_id == p['product_id']:
                            add = False
                    if add:
                        prods.append(prod)

                cr.commit()

                thread1 = threading.Thread(target=self.core_sync_products_thread, args=(cr.dbname, uid, magento_app.id, prods, store_view, context))
                thread1.start()

        return True

    def core_sync_products_thread(self, db_name, uid, magento_app, products, store_view, context=None):
        """Thread Sync Products
        :magento_app: Magento APP ID (int)
        :products: Dicc
        :context: Dicc
        return True/False
        """

        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()

        magento_app = self.pool.get('magento.app').browse(cr, uid, magento_app)

        # We have list first product simple and after product configurable
        # First, only create product configurable (and product simple related in this product configurable)
        # After, create product simple. If this simple was created, skip
        for product in products:
            if product['type'] == 'configurable':
                self.pool.get('product.product').magento_create_product_type(cr, uid, magento_app, product, store_view, context)

        #Uncomment second part import only configurable products (id from to)
        for product in products:
            if product['type'] != 'configurable':
                self.pool.get('product.product').magento_create_product_type(cr, uid, magento_app, product, store_view, context)

        LOGGER.notifyChannel('Magento App', netsvc.LOG_INFO, "End Sync Products magento app %s." % (magento_app.name))
        self.pool.get('magento.log').create_log(cr, uid, magento_app, 'product.product', 0, '', 'done', _('Finish Import/Update products') )

        cr.close()

        return True

magento_app()
