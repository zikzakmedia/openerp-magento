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

try:
    from magento import api
except:
    raise osv.except_osv(_('vobject Import Error!'), _('Please install python-magento from https://github.com/zikzakmedia/magento'))

from magento import *

mgn2oerp_type_fields = {
    'text':'char',
    'textarea':'text',
    'boolean':'boolean',
    'select':'selection',
    #~ 'multiselect':'many2many', #TODO
    'date':'datetime',
    'price':'float',
}

class magento_storeview(osv.osv):
    _name = 'magento.storeview'
    _description = 'Magento Store View'

magento_storeview()

class magento_app(osv.osv):
    _name = 'magento.app'
    _description = 'Magento Server - APP'

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'uri': fields.char('URI', size=256, required=True, help='URI Magento App. http://yourmagento.com/ (with / at end URI)'),
        'username': fields.char('Username', size=256, required=True),
        'password': fields.char('Password', size=256, required=True),
        'product_category_id': fields.many2one('product.category', 'Root product Category', required=True),
        'magento_website_ids': fields.one2many('magento.website', 'magento_app_id', 'Websites'),
        'payment_default_id': fields.many2one('account.payment.term', 'Default Payment Term', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True),
        'from_import_products': fields.datetime('From Import Products', help='This date is last import. If you need import new products, you can modify this date (filter)'),
        'to_import_products': fields.datetime('To Import Products', help='This date is to import (filter)'),
        'last_export_product_category': fields.datetime('Last Export Categories', help='This date is to export (filter)'),
        'magento_default_storeview': fields.many2one('magento.storeview', 'Store View Default', help='Default language this shop. If not select, use lang user'),
        'from_import_customers': fields.datetime('From Import Customers', help='This date is last import. If you need import new partners, you can modify this date (filter)'),
        'to_import_customers': fields.datetime('To Import Customers', help='This date is to import (filter)'),
    }

    def core_sync_test(self, cr, uid, ids, context):
        """
        def test connection OpenERP to Magento
        """

        for magento_app in self.browse(cr, uid, ids):
            status = {}
            try:
                with API(magento_app.uri, magento_app.username, magento_app.password) as magento_api:
                    websites = magento_api.call('ol_websites.list', [])
                    if len(websites) > 0:
                        status =  {'title':_('Ok!'), 'message': _('Connection to server are successfully.')}
                    else:
                        status =  {'title':_('Warning!'), 'message': _('Connection to server are successfully but reconfigure your Magento.')}
            except:
                status =  {'title':_('Error!'), 'message': _('Connection to server failed.')}

            raise osv.except_osv(status['title'], status['message'])

    def core_sync_store(self, cr, uid, ids, context):
        """
        Sync Store Magento to OpenERP
        - Websites
        - Store Group / OpenERP Sale Shop
        - Store View
        Only create new values if not exist; not update or delete
        :return True
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            with API(magento_app.uri, magento_app.username, magento_app.password) as magento_api:

                """Websites"""
                for website in magento_api.call('ol_websites.list', []):
                    web_site = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'magento.website', website['default_group_id'])

                    if not web_site: #create
                        values = {
                            'name': website['name'],
                            'code': website['code'],
                            'magento_app_id': magento_app.id,
                        }
                        website_oerp_id = self.pool.get('magento.website').create(cr, uid, values, context)
                        self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'magento.website', website_oerp_id, website['default_group_id'])
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Website: magento %s, magento website id %s." % (magento_app.name, website['default_group_id']))
                        """Sale Shop"""
                        values = {
                            'name': website['name'],
                            'payment_default_id': magento_app.payment_default_id.id,
                            'warehouse_id': magento_app.warehouse_id.id,
                            'pricelist_id': magento_app.pricelist_id.id,
                            'magento_shop': True,
                            'magento_website': website_oerp_id,
                        }
                        saleshop_oerp_id = self.pool.get('sale.shop').create(cr, uid, values, context)
                        self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'sale.shop', saleshop_oerp_id, website['default_group_id'])
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Sale Shop: magento %s, Sale Shop id %s." % (magento_app.name, saleshop_oerp_id))
                    else:
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_ERROR, "Skip! Website exists: magento %s, magento website id %s. Not create" % (magento_app.name, website['default_group_id']))

                """Store Group"""
                for storegroup in magento_api.call('ol_groups.list', []):
                    store_group = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'magento.storegroup', storegroup['group_id'])

                    if not store_group: #create
                        magento_website_id = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'magento.website', storegroup['website_id'])

                        if magento_website_id:
                            external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [magento_website_id])
                            values = {
                                'name': storegroup['name'],
                                'magento_app_id': magento_app.id,
                                'magento_website_id': external_referentials[0]['oerp_id'],
                            }
                            storegroup_oerp_id = self.pool.get('magento.storegroup').create(cr, uid, values, context)
                            self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'magento.storegroup', storegroup_oerp_id, storegroup['group_id'])
                            logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Store Group: magento %s, magento store group id %s." % (magento_app.name, storegroup['group_id']))
                        else:
                            logger.notifyChannel('Magento Sync API', netsvc.LOG_ERROR, "Failed to find magento.website with magento %s and Magento ID %s. Not create Store Group." % (magento_app.name, storegroup['default_group_id']))
                    else:
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_ERROR, "Skip! Store Group exists: magento %s, magento store group id %s. Not create" % (magento_app.name, storegroup['group_id']))

                """Store View"""
                for storeview in magento_api.call('ol_storeviews.list', []):
                    store_view = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'magento.storeview', storeview['store_id'])

                    if not store_view: #create
                        store_group = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'magento.storegroup', storeview['group_id'])
                        external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_group])
                        if len(external_referentials)>0:
                            values = {
                                'name': storeview['name'],
                                'code': storeview['code'],
                                'magento_storegroup_id': external_referentials[0]['oerp_id'],
                            }
                            storeview_oerp_id = self.pool.get('magento.storeview').create(cr, uid, values, context)
                            self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'magento.storeview', storeview_oerp_id, storeview['store_id'])
                            logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Store View: magento app id %s, magento store view id %s." % (storeview_oerp_id, storeview['store_id']))
                        else:
                            logger.notifyChannel('Magento Sync API', netsvc.LOG_ERROR, "Failed to find magento.storegroup with magento %s and Magento ID %s. Not create Store Group." % (magento_app.name, storeview['group_id']))
                    else:
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Skip! Store Group exists: magento %s, magento store group id %s. Not create" % (magento_app.name, storeview['store_id']))
        return True

    def core_sync_attributes_set(self, cr, uid, ids, context):
        """
        def sync Attributes Set (group attribute) Magento to OpenERP
        Only create new values if not exist; not update or delete
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            with ProductAttributeSet(magento_app.uri, magento_app.username, magento_app.password) as product_attribute_set_api:
                for product_attribute_set in product_attribute_set_api.list():
                    attribute_set = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.attributes.group', product_attribute_set['set_id'])

                    if not attribute_set: #create
                        values = {
                            'name': product_attribute_set['name'],
                            'code': product_attribute_set['name'],
                            'magento': True,
                        }
                        attribute_group_oerp_id = self.pool.get('product.attributes.group').create(cr, uid, values, context)
                        self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.attributes.group', attribute_group_oerp_id, product_attribute_set['set_id'])
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Attribute Group: magento %s, magento attribute set id %s." % (magento_app.name, product_attribute_set['set_id']))
                    else:
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Skip! Attribute Group exists: magento %s, magento attribute set id %s. Not create" % (magento_app.name, product_attribute_set['set_id']))
        return True

    def core_sync_attributes(self, cr, uid, ids, context):
        """
        def sync Attributes Magento to OpenERP
        Only create new values if not exist; not update or delete
        Notes:
         - Selection field not more 128 characters. More fields, need create many2one field manually
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            with ProductAttribute(magento_app.uri, magento_app.username, magento_app.password) as  product_attribute_api:
                product_attributes = self.pool.get('product.attributes.group').search(cr, uid, [('magento','=',True)])

                prod_attribute_oerp_ids  = []
                for prod_attribute in self.pool.get('product.attributes.group').browse(cr, uid, product_attributes):
                    external_referential = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.attributes.group', prod_attribute.id)
                    external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [external_referential])
                    if len(external_referentials)>0:
                        for product_attribute in product_attribute_api.list(external_referentials[0]['mgn_id']):
                            #this attribute is exclude?
                            product_attribute_excludes = self.pool.get('magento.attribute.exclude').search(cr, uid, [('name','=',product_attribute['code'])])
                            if not len(product_attribute_excludes)>0:
                                attribute = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'magento.website', product_attribute['attribute_id'])

                                if not attribute: #create
                                    type = False
                                    if not product_attribute['type'] == '': #title attributes magento are empty
                                        if product_attribute['type'] in mgn2oerp_type_fields:
                                            type = mgn2oerp_type_fields[product_attribute['type']]
                                    if type:
                                        values = {
                                            'name': 'x_'+str(product_attribute['code']),
                                            'field_description': product_attribute['code'],
                                            'ttype': type,
                                            'translate':False,
                                            'required':False,
                                        }

                                        if type == 'selection':
                                            options = product_attribute_api.options(product_attribute['code'])
                                            """
                                            selection field are 128 characters. More, create many2one field
                                            option_oerp = str([('',''),('','')])
                                            """
                                            options_oerp = []
                                            for option in options:
                                                options_oerp.append("('"+str(option['value'])+"','"+str(option['label'].encode('utf-8'))+"')")
                                            option_oerp = ','.join(str(n) for n in options_oerp)
                                            values['selection'] = '['+option_oerp+']'

                                            if len(values['selection']) > 128:
                                                values = False
                                                logger.notifyChannel('Magento Sync Attribute', netsvc.LOG_INFO, "Skip! Attribute type selection long: magento %s, magento attribute id %s, attribute type %s. Not create" % (magento_app.name, product_attribute['code'], product_attribute['type']))

                                        if values:
                                            #if this attribute not exists:
                                            product_attributes = self.pool.get('product.attributes').search(cr, uid, [('name','=',values['name'])])
                                            if not len(product_attributes)>0:
                                                product_attribute_oerp_id = self.pool.get('product.attributes').create(cr, uid, values, context)
                                                self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'magento.website', product_attribute_oerp_id, product_attribute['attribute_id'])
                                                cr.commit()
                                                logger.notifyChannel('Magento Sync Attribute', netsvc.LOG_INFO, "Create Attribute Product: magento %s, magento attribute code %s." % (magento_app.name, product_attribute['code']))
                                            else:
                                                product_attribute_oerp_id = product_attributes[0]
                                                logger.notifyChannel('Magento Sync Attribute', netsvc.LOG_INFO, "Skip! Create Attribute Product: magento %s, magento attribute code %s. This attribute exist another mapping or manual" % (magento_app.name, product_attribute['code']))
                                            #add list relation group <-> attribute
                                            prod_attribute_oerp_ids.append(product_attribute_oerp_id)
                                    else:
                                        logger.notifyChannel('Magento Sync Attribute', netsvc.LOG_INFO, "Skip! Attribute type not suport: magento %s, magento attribute id %s, attribute type %s. Not create" % (magento_app.name, product_attribute['code'], product_attribute['type']))
                                else:
                                    logger.notifyChannel('Magento Sync Attribute', netsvc.LOG_INFO, "Skip! Attribute exists: magento %s, magento attribute id %s. Not create" % (magento_app.name, product_attribute['code']))

                    #save attributes relation at product_attribute_group
                    if len(prod_attribute_oerp_ids)>0:
                        self.pool.get('product.attributes.group').write(cr, uid, [prod_attribute.id], {'product_att_ids': [(6, 0, prod_attribute_oerp_ids)], })
        return True

    def core_sync_categories(self, cr, uid, ids, context):
        """
        def sync Categories Catalog Magento to OpenERP
        Only create new values if not exist; not update or delete
        Category extraction values and creation is magento_record_entire_tree function at product.category model
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            with Category(magento_app.uri, magento_app.username, magento_app.password) as category_api:
                categ_tree = category_api.tree()
                self.pool.get('product.category').magento_record_entire_tree(cr, uid, magento_app, categ_tree)

        logger.notifyChannel('Magento Sync Categories', netsvc.LOG_INFO, "End Sync Categories magento app %s." % (magento_app.name))
        return True

    def core_export_categories(self, cr, uid, ids, context):
        """
        def export Product Categories OpenERP to Magento
        :ids list
        :return True
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            product_categories = self.pool.get('product.category').search(cr, uid, [('parent_id', 'child_of', magento_app.product_category_id.id)], context=context)
            product_categories.remove(magento_app.product_category_id.id) #remove top parent category
            for product_category in product_categories:
                product_cat_mgn_id = False
                context["category_id"] = product_category
                product_category_vals = self.pool.get('base.external.mapping').get_oerp_to_external(cr, uid, 'magento.product.category', [product_category], context)[0]

                product_cat = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.category', product_category_vals['id'])
                if product_cat:
                    product_cat = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [product_cat])
                    product_cat_mgn_id = product_cat[0]['mgn_id']

                del product_category_vals['id']

                with Category(magento_app.uri, magento_app.username, magento_app.password) as category_api:
                    try:
                        if product_cat_mgn_id:
                            #TODO Parent ID not updated. Only vals
                            category_api.update(product_cat_mgn_id, product_category_vals)
                            logger.notifyChannel('Magento Export Categories', netsvc.LOG_INFO, "Update Category Magento ID %s, OpenERP ID %s." % (product_cat_mgn_id, product_category))
                        else:
                            product_cat_parent = product_category_vals['parent_id']
                            product_cat_parent = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'product.category', product_cat_parent)
                            if product_cat_parent:
                                product_cat_parent = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [product_cat_parent])
                                parent_id = product_cat_parent[0]['mgn_id']

                            del product_category_vals['parent_id']
                            product_cat_mgn_id = category_api.create(parent_id, product_category_vals)
                            self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.category', product_category, product_cat_mgn_id)
                            logger.notifyChannel('Magento Export Categories', netsvc.LOG_INFO, "Create Category Magento ID %s, OpenERP ID %s." % (product_cat_mgn_id, product_category))
                    except:
                        logger.notifyChannel('Magento Export Categories', netsvc.LOG_ERROR, "Error to export Category OpenERP ID %s." % (product_category))

            logger.notifyChannel('Magento Export Categories', netsvc.LOG_INFO, "End export product categories to magento %s." % (magento_app.name))

            self.write(cr, uid, ids, {'last_export_product_category': time.strftime('%Y-%m-%d %H:%M:%S')})

        return True

    def core_sync_product_type(self, cr, uid, ids, context):
        """
        def sync Product Type Magento to OpenERP
        Only create new values if not exist; not update or delete
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            with ProductTypes(magento_app.uri, magento_app.username, magento_app.password) as product_type_api:
                for product_type in product_type_api.list():
                    prod_type_ids = self.pool.get('magento.product.product.type').search(cr, uid, [('product_type','=',product_type['type'])])

                    if not len(prod_type_ids) > 0: #create
                        values = {
                            'name': product_type['label'],
                            'product_type': product_type['type'],
                        }
                        product_type_oerp_id = self.pool.get('magento.product.product.type').create(cr, uid, values, context)
                        logger.notifyChannel('Magento Sync Product Type', netsvc.LOG_INFO, "Create Product Type: magento app %s, product type %s." % (magento_app.name, product_type['type']))
                    else:
                        logger.notifyChannel('Magento Sync Product Type', netsvc.LOG_INFO, "Skip! Product Type exists: %s. Not create" % (product_type['type']))

        return True

    def core_sync_products(self, cr, uid, ids, context):
        """
        def sync Product Product Magento to OpenERP
        Only create new values if not exist; not update or delete
        :ids list
        :return True
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):

            if not magento_app.magento_default_storeview:
                raise osv.except_osv(_("Alert"), _("Select Store View Magento"))

            with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
                ofilter = {'created_at':{'from':magento_app.from_import_products, 'to':magento_app.to_import_products}}

                store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', magento_app.magento_default_storeview.id)
                store_view = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])
                store_view = store_view[0]['mgn_id']

                #~ Update date last import
                date_from_import = magento_app.to_import_products and magento_app.to_import_products or time.strftime('%Y-%m-%d %H:%M:%S')
                self.write(cr, uid, ids, {'from_import_products': date_from_import})
                self.write(cr, uid, ids, {'to_import_products': time.strftime('%Y-%m-%d %H:%M:%S')})

                for product in product_api.list(ofilter, store_view):
                    product_product = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.product', product['product_id'])

                    if not product_product: #create
                        external_referential_id = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.attributes.group', product['set'])
                        attribute_external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [external_referential_id])

                        category_ids = []
                        for cat_id in product['category_ids']:
                            category_id = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.category', cat_id)
                            external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [category_id])
                            category_ids.append(external_referentials[0]['oerp_id'])

                        values = {
                            'name': product['name'],
                            'magento_sku': product['sku'],
                            'default_code': product['sku'],
                            'magento_exportable': True,
                            'magento_product_type': product['type'],
                            'categ_id':magento_app.product_category_id.id,
                            'attribute_group_id': attribute_external_referentials[0]['oerp_id'],
                            'type': 'product',
                        }

                        if len(category_ids)>0:
                            values['categ_ids'] = [(6, 0, category_ids)]

                        product_product_oerp_id = self.pool.get('product.product').create(cr, uid, values, context)
                        self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.product', product_product_oerp_id, product['product_id'])
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Product Product: magento app %s, openerp id %s, magento product id %s." % (magento_app.name, product_product_oerp_id, product['product_id']))

                        #~ Update product info
                        product_info = product_api.info(product['sku'], store_view)

                        product_obj = self.pool.get('product.product').browse(cr, uid, product_product_oerp_id, context)

                        context['magento_app'] = magento_app
                        product_product_vals = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.product', product_product_oerp_id, product_info, context)
                        product_template_vals = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.template', product_obj.product_tmpl_id.id, product_info, context)
                        vals = dict(product_product_vals, **product_template_vals)
                        #~ print vals #dicc value to write
                        self.pool.get('product.product').write(cr, uid, [product_product_oerp_id], vals)
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Write Product Product: magento %s, openerp id %s, magento product id %s." % (magento_app.name, product_product_oerp_id, product['product_id']))

                        cr.commit()
                    else:
                        logger.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Skip! Product exists: magento %s, magento product id %s. Not create" % (magento_app.name, product['product_id']))

        return True

    def core_sync_images(self, cr, uid, ids, context):
        """
        def sync Images from Magento to OpenERP
        Only create new values if not exist; not update or delete
        :ids list
        :return True
        """

        logger = netsvc.Logger()

        magento_external_referential_obj = self.pool.get('magento.external.referential')
        product_image_magento_app_obj = self.pool.get('product.images.magento.app')
        product_images_obj = self.pool.get('product.images')

        for magento_app in self.browse(cr, uid, ids):

            with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
                magento_external_referential_ids = magento_external_referential_obj.search(cr, uid, [('model_id.model', '=', 'product.product'), ('magento_app_id', 'in', [magento_app.id])], context = context)
                product_ids = magento_external_referential_obj.read(cr, uid, magento_external_referential_ids, ['oerp_id', 'mgn_id'], context)

                for product_id in product_ids:
                    with ProductImages(magento_app.uri, magento_app.username, magento_app.password) as product_image_api:
                        for product_image in product_image_api.list(product_id['mgn_id']):
                            image_ids = product_images_obj.search(cr, uid, [('filename', '=', product_image['url'])], context = context)
                            if len(image_ids) > 0:
                                product_image_magento_ids = product_image_magento_app_obj.search(cr, uid, [('magento_app_id', '=', magento_app.id), ('product_images_id', 'in', image_ids)], context=context)
                                if len(product_image_magento_ids) > 0: #exist
                                    logger.notifyChannel('Magento Sync Images', netsvc.LOG_INFO, "Image skipped! Image for this product in this Magento App already exists. Not created.")
                                    continue

                            name = product_image['label']
                            if not name:
                                splited_name = product_image['file'].split('/')
                                name = splited_name[len(splited_name)-1]

                            vals = {
                                'name': name,
                                'link': True,
                                'filename': product_image['url'],
                                'magento_exclude': product_image['exclude'],
                                'magento_position': product_image['position'],
                                'product_id': product_id['oerp_id'],
                                'magento_filename': product_image['file'],
                                'magento_exportable': True,
                                'magento_app_ids': [(6, 0, [magento_app.id])],
                            }
                            product_images_id =  product_images_obj.create(cr, uid, vals, context)
                            prod_image_mgn_app_ids = product_image_magento_app_obj.search(cr, uid, [('product_images_id','=',product_images_id),('magento_app_id','=',magento_app.id)])
                            if len(prod_image_mgn_app_ids)>0:
                                product_image_magento_app_obj.write(cr, uid, prod_image_mgn_app_ids, {'magento_exported':True})

                            logger.notifyChannel('Magento Sync Images', netsvc.LOG_INFO, " Magento %s, Image %s created, Product ID %s" % (magento_app.name, name, product_id['oerp_id']))
        return True


    def core_sync_customer_group(self, cr, uid, ids, context):
        """
        def sync Customer Group from Magento to OpenERP
        Only create new values if not exist; not update or delete
        :ids list
        :return True
        """

        logger = netsvc.Logger()

        for magento_app in self.browse(cr, uid, ids):
            with CustomerGroup(magento_app.uri, magento_app.username, magento_app.password) as customer_group_api:
                for customer_group in customer_group_api.list():
                    group_ids = self.pool.get('magento.customer.group').search(cr, uid, [('customer_group_id', '=', customer_group['customer_group_id']), ('magento_app_id', 'in', [magento_app.id])])
                    if len(group_ids)>0:
                        logger.notifyChannel('Magento Sync Customer Group', netsvc.LOG_INFO, "Skip! Magento %s: Group %s already exists. Not created." % (magento_app.name, customer_group['customer_group_code']))
                        continue
                    
                    values = {
                        'name': customer_group['customer_group_code'],
                        'customer_group_id': customer_group['customer_group_id'],
                        'magento_app_id': magento_app.id,
                    }
                    magento_customer_group_id = self.pool.get('magento.customer.group').create(cr, uid, values)
                    self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'magento.customer.group', magento_customer_group_id, customer_group['customer_group_id'])

                    logger.notifyChannel('Magento Sync Customer Group', netsvc.LOG_INFO, "Magento %s: Group %s created." % (magento_app.name, customer_group['customer_group_code']))

        return True
        
    def core_sync_customers(self, cr, uid, ids, context):
        """
        def sync Customer from Magento to OpenERP
        Only create new values if not exist; not update or delete
        :ids list
        :return True
        """

        logger = netsvc.Logger()

        print "TODO"

        return True

magento_app()

class magento_website(osv.osv):
    _name = 'magento.website'
    _description = 'Magento Website'

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'code': fields.char('Code', size=256, required=True),
        'magento_app_id': fields.many2one('magento.app', 'Magento App', required=True),
        'magento_storegroup_ids': fields.one2many('magento.storegroup', 'magento_website_id', 'Store Group'),
        'sale_shop': fields.one2many('sale.shop', 'magento_website', 'Sale Shop'),
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Website not allow to delete"))

magento_website()

class magento_storegroup(osv.osv):
    _name = 'magento.storegroup'
    _description = 'Magento Store Group'

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'magento_website_id': fields.many2one('magento.website', 'Magento Website', required=True),
        'magento_storeview_ids': fields.one2many('magento.storeview', 'magento_storegroup_id', 'Store View'),
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Store Group not allow to delete"))

magento_storegroup()

class magento_storeview(osv.osv):
    _name = 'magento.storeview'
    _description = 'Magento Store View'

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'code': fields.char('Code', size=256, required=True),
        'magento_storegroup_id': fields.many2one('magento.storegroup', 'Magento Store Group', required=True),
        'language_id': fields.many2one('res.lang', 'Language Default'),
        'magento_last_import_locale_products': fields.datetime('Last Import Products'),
        'magento_last_export_locale_products': fields.datetime('Last Export Products'),
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Store View not allow to delete"))

    def magento_import_locale_products(self, cr, uid, ids, context=None):
        """
        Get all IDs products to write locale to OpenERP)
        Use Base External Mapping to transform values
        :return True
        """

        logger = netsvc.Logger()

        product_shop_ids = []
        for storeview in self.browse(cr, uid, ids):
            if not storeview.language_id:
                logger.notifyChannel('Magento Store View', netsvc.LOG_INFO, "Select language available this store view")
                raise osv.except_osv(_("Alert"), _("Select language available this store view"))

            last_exported_time = storeview.magento_last_import_locale_products
            magento_app = storeview.magento_storegroup_id.magento_website_id.magento_app_id

            context['lang'] = storeview.language_id.code
            context['magento_app'] = magento_app

            for shop in storeview.magento_storegroup_id.magento_website_id.sale_shop:
                product_shop_ids = self.pool.get('product.product').search(cr, uid, [('magento_exportable','=',True),('magento_sale_shop','in',shop.id)])

            for product in self.pool.get('product.product').browse(cr, uid, product_shop_ids):
                store_view = self.pool.get('magento.external.referential').check_oerp2mgn(cr, uid, magento_app, 'magento.storeview', storeview.id)
                store_view = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [store_view])
                store_view = store_view[0]['mgn_id']

                with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
                    product_info = product_api.info(product['magento_sku'],store_view)

                    product_obj = self.pool.get('product.product').browse(cr, uid, product.id, context)

                    product_product_vals = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.product', product.id, product_info, context)
                    product_template_vals = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.template', product_obj.product_tmpl_id.id, product_info, context)
                    vals = dict(product_product_vals, **product_template_vals)
                    #~ print vals #dicc value to write
                    self.pool.get('product.product').write(cr, uid, [product.id], vals, context)
                    logger.notifyChannel('Magento Store View', netsvc.LOG_INFO, "Write Product Product Locale: magento %s, openerp id %s, magento product id %s." % (magento_app.name, product.id, product_info['product_id']))

                    cr.commit()

            self.write(cr, uid, ids, {'magento_last_import_locale_products': time.strftime('%Y-%m-%d %H:%M:%S')})

        return True

    def magento_export_locale_products(self, cr, uid, ids, context=None):
        """
        Get all IDs products to write locale to Magento (store))
        Use Base External Mapping to transform values
        :return True
        """

        logger = netsvc.Logger()

        product_shop_ids = []
        for storeview in self.browse(cr, uid, ids):
            if not storeview.language_id:
                logger.notifyChannel('Magento Store View', netsvc.LOG_INFO, "Select language available this store view")
                raise osv.except_osv(_("Alert"), _("Select language available this store view"))

            last_exported_time = storeview.magento_last_export_locale_products
            magento_app = storeview.magento_storegroup_id.magento_website_id.magento_app_id

            for shop in storeview.magento_storegroup_id.magento_website_id.sale_shop:
                product_product_ids = self.pool.get('product.product').search(cr, uid, [('magento_exportable','=',True),('magento_sale_shop','in',shop.id)])

                for product_product in self.pool.get('product.product').perm_read(cr, uid, product_product_ids):
                    # product.product create/modify > date exported last time
                    if last_exported_time < product_product['create_date'][:19] or (product_product['write_date'] and last_exported_time < product_product['write_date'][:19]):
                        product_shop_ids.append(product_product['id'])

            context['shop'] = shop
            context['lang'] = storeview.language_id.code
            context['store_view'] = storeview

            self.pool.get('sale.shop').magento_export_products_stepbystep(cr, uid, magento_app, product_shop_ids, context)
            logger.notifyChannel('Magento Store View', netsvc.LOG_INFO, "Products to export: %s" % (product_shop_ids))

            self.write(cr, uid, ids, {'magento_last_export_locale_products': time.strftime('%Y-%m-%d %H:%M:%S')})

        return True

magento_storeview()

class magento_attribute_exclude(osv.osv):
    _name = 'magento.attribute.exclude'
    _description = 'Magento Attributes Exclude'

    _columns = {
        'name': fields.char('Code', size=256, required=True),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, select=True, ondelete='cascade'),
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Attribute Exclude not allow to delete"))

magento_attribute_exclude()

class magento_customer_group(osv.osv):
    _name = 'magento.customer.group'
    _description = 'Magento Customer Group'
    
    _columns = {
        'name': fields.char('Name', size=256, required=True, readonly=True),
        'customer_group_id': fields.integer('Customer Group ID', required=True, readonly=True),
        'magento_app_id': fields.many2one('magento.app', 'Magento App', required=True, readonly=True),
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Customer Group not allow to delete"))

magento_customer_group()

class magento_app_customer(osv.osv):
    _name = 'magento.app.customer'
    _description = 'Magento App Customer'
    _rec_name = "partner_id"

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'magento_app_id': fields.many2one('magento.app','Magento App', required=True),
        'magento_customer_group_id': fields.many2one('magento.customer.group','Customer Group', required=True), #TODO: Domain
        'magento_storeview_id':fields.many2one('magento.storeview', 'Last Store View', readonly=True, help="Last store view where the customer has bought."),
        'magento_storeview_ids':fields.many2many('magento.storeview', 'magento_storeid_rel', 'partner_id', 'store_id', 'Store Views', readonly=True),
        'magento_emailid':fields.char('Email Address', size=100, required=True, help="Magento uses this email ID to match the customer."),
        'magento_vat':fields.char('Magento VAT', size=50, readonly=True, help="To be able to receive customer VAT number you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
        #~ 'magento_birthday':fields.date('Birthday', help="To be able to receive customer birthday you must set it in Magento Admin Panel, menu System / Configuration / Client Configuration / Name and Address Options."),
        #~ 'magento_newsletter':fields.boolean('Newsletter'),
    }

    #~ TODO: Constrain partner_id and magento_app_id

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Websites/Groups not allow to delete"))

magento_app_customer()
