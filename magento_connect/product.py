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
import unicodedata
import re

LOGGER = netsvc.Logger()

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """

    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)

class magento_product_category_attribute_options(osv.osv):
    _name = "magento.product_category_attribute_options"
    _description = "Option products category Attributes"
    _rec_name = "label"

    def _get_default_option(self, cr, uid, field_name, value, context=None):
        res = self.search(cr, uid, [['attribute_name', '=', field_name], ['value', '=', value]], context=context)
        return res and res[0] or False


    def get_create_option_id(self, cr, uid, value, attribute_name, context=None):
        id = self.search(cr, uid, [['attribute_name', '=', attribute_name], ['value', '=', value]], context=context)
        if id:
            return id[0]
        else:
            return self.create(cr, uid, {
                                'value': value,
                                'attribute_name': attribute_name,
                                'label': value.replace('_', ' '),
                                }, context=context)

    _columns = {
        'attribute_name':fields.char(string='Attribute Code', size=64),
        'value':fields.char('Value', size=200),
        'label':fields.char('Label', size=100),
    }

magento_product_category_attribute_options()

class product_category(osv.osv):
    _inherit = "product.category"

    def onchange_name(self, cr, uid, ids, name, slug):
        value = {}
        if not slug:
            slug = slugify(unicode(name, 'UTF-8'))
            value = {'magento_url_key': slug}
        return {'value':value}

    _columns = {
        'magento_exportable':fields.boolean('Exported to Magento?', change_default=True,),
        'magento_is_active': fields.boolean('Active?', help="Indicates whether active in magento"),
        'magento_description': fields.text('Description'),
        'magento_meta_title': fields.text('Meta Title'),
        'magento_meta_keywords': fields.text('Meta Keyword'),
        'magento_meta_description': fields.text('Meta Description'),
        'magento_available_sort_by': fields.many2one('magento.product_category_attribute_options', 'Available Product Listing (Sort By)', domain="[('attribute_name', '=', 'available_sort_by')]"),
        'magento_default_sort_by': fields.many2one('magento.product_category_attribute_options', 'Default Product Listing Sort (Sort By)', domain="[('attribute_name', '=', 'default_sort_by')]"),
        'magento_url_key': fields.char('URL-key', size=100, translate=True),
        'magento_include_in_menu': fields.boolean('Include in menu'),
    }

    _defaults = {
        # 'magento_available_sort_by': lambda self,cr,uid,c: self.pool.get('magento.product_category_attribute_options')._get_default_option(cr, uid, 'available_sort_by', 'None', context=c),
        # 'magento_default_sort_by': lambda self,cr,uid,c: self.pool.get('magento.product_category_attribute_options')._get_default_option(cr, uid, 'default_sort_by', 'None', context=c),
        'magento_include_in_menu': lambda * a: 1,
        'magento_is_active': lambda * a: 1,
    }

    def copy(self, cr, uid, id, default={}, context=None, done_list=[], local=False):
        """ 
        When copy, magento url key add -copy if exist magento_url_key
        """

        category = self.browse(cr, uid, id, context=context)
        if not default:
            default = {}
        if category.magento_url_key:
            default = default.copy()
            slug = category.magento_url_key
            while self.search(cr, uid, [('magento_url_key', '=', slug)]):
                slug += _('-copy')
            default['magento_url_key'] = slug
        return super(product_category, self).copy(cr, uid, id, default, context=context)

    def magento_record_entire_tree(self, cr, uid, magento_app, categ_tree, context={}):
        """
        For categories magento { children:[ {} ]}
        Call magento_record_category to add values
        """
        self.magento_record_category(cr, uid, magento_app, int(categ_tree['category_id']))
        for each in categ_tree['children']:
            self.magento_record_entire_tree(cr, uid, magento_app, each, context={})
        return True

    def magento_record_category(self, cr, uid, magento_app, category_id, context={}):
        """
        Get Category Info Magento and create or skip category
        """

        from magento import Category

        with Category(magento_app.uri, magento_app.username, magento_app.password) as category_api:
            category = category_api.info(category_id)
            #~ print category['name'], category['category_id'], category['parent_id']
            LOGGER.notifyChannel('Magento Sync Categories', netsvc.LOG_INFO, "Name: %s. ID: %s. Parent ID: %s" % (category['name'], category['category_id'], category['parent_id']))
            magento_cat_id = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.category', category['category_id'])

            if not magento_cat_id:
                mgn_parent_id = category['parent_id']
                if category['parent_id'] == 0:
                    mgn_parent_id = magento_app.product_category_id.id

                product_category_oerp_ids = self.pool.get('magento.external.referential').get_mgnreferential_ids(cr, uid, magento_app, 'product.category', [mgn_parent_id])

                parent_id = magento_app.product_category_id.id
                if len(product_category_oerp_ids) > 0:
                    parent_id = self.pool.get('magento.external.referential').get_external_referential(cr, uid, product_category_oerp_ids)[0]['oerp_id']

                context['parent_id'] = parent_id

                values = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.category', '', category, context)
                values['magento_exportable'] = True

                product_category_oerp_id = self.pool.get('product.category').create(cr, uid, values, context)
                self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.category', product_category_oerp_id, category['category_id'])
                cr.commit()
                LOGGER.notifyChannel('Magento Sync Product Category', netsvc.LOG_INFO, "Create Product Category: openerp id %s, magento id %s." % (product_category_oerp_id, category['category_id']))
            else:
                LOGGER.notifyChannel('Magento Sync Product Category', netsvc.LOG_INFO, "Skip! Product Category exists: openerp id %s, magento id %s." % (category['category_id'], magento_cat_id))

product_category()

class magento_product_product_type(osv.osv):
    _name = 'magento.product.product.type'
    _description = 'Magento Product Type'

    _columns = {
        'name': fields.char('Name', size=100, required=True, translate=True),
        'product_type': fields.char('Type', size=100, required=True, help="Use the same name of Magento product type, for example 'simple'"),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the product without removing it."),
    }

    _defaults = {
        'active': lambda * a: 1,
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Magento Product Type not allow to delete"))

magento_product_product_type()

class product_product(osv.osv):
    _inherit = "product.product"

    def _product_type_get(self, cr, uid, context=None):
        ids = self.pool.get('magento.product.product.type').search(cr, uid, [('active', '=', True)], order='id')
        product_types = self.pool.get('magento.product.product.type').read(cr, uid, ids, ['product_type', 'name'], context=context)
        return [(pt['product_type'], pt['name']) for pt in product_types]

    def onchange_name(self, cr, uid, ids, name, slug):
        value = {}
        if not slug and name:
            slug = slugify(unicode(name, 'UTF-8'))
            value = {'magento_url_key': slug}
        return {'value':value}

    def _check_magento_sku(self, cr, uid, magento_sku, id=False):
        """Check if this Magento SKU exists another product
        :param id int
        :magento_sku = str
        :return True/False
        """
        condition = [('magento_sku', '=', magento_sku), ('magento_exportable', '=', True)]
        if id:
            condition.append(('id', '!=', id))
        prods = self.search(cr, uid, condition)
        if len(prods) > 0:
            return True
        return False

    _columns = {
        'magento_sku':fields.char('Magento SKU', size=64),
        'magento_exportable':fields.boolean('Exported to Magento?', change_default=True, help='If check this value, this product is publishing in Magento Store. For disable this product in your Magento Store, change visibility option to Nowhere.'),
        'magento_sale_shop': fields.many2many('sale.shop', 'magento_sale_shop_rel', 'product_product_id', 'sale_shop_id', 'Websites', help='Select yours Sale Shops available this product'),
        'magento_product_type': fields.selection(_product_type_get, 'Product Type'),
        'magento_status':fields.boolean('Status'),
        'magento_visibility': fields.selection([('0', 'Select Option'), ('1', 'Nowhere'), ('2', 'Catalog'), ('3', 'Search'), ('4', 'Catalog,Search')], 'Visibility'),
        'magento_url_key': fields.char('Url Key', size=256),
        'magento_shortdescription': fields.text('Short Description', translate=True),
        'magento_metadescription': fields.text('Description', translate=True),
        'magento_metakeyword': fields.text('Keyword', translate=True),
        'magento_metatitle': fields.char('Title', size=256, translate=True),
        'magento_manage_stock':fields.boolean('Manage Stock'),
    }

    _defaults = {
        'magento_status':lambda * a:True,
        'magento_visibility': '4',
        'magento_manage_stock':lambda * a:True,
    }

    def create(self, cr, uid, vals, context=None):
        """Convert url key slug line"""

        if 'magento_sku' in vals and vals['magento_sku'] is not False:
            if self._check_magento_sku(cr, uid, vals['magento_sku']):
                raise osv.except_osv(_("Alert"), _("Error! Magento SKU %s must be unique") % (vals['magento_sku']))

        if 'magento_url_key' in vals:
            slug = vals['magento_url_key']
            if not isinstance(slug, unicode):
                slug = unicode(slug, 'UTF-8')
            slug = slugify(slug)
            vals['magento_url_key'] = slug

        product_id = super(product_product, self).create(cr, uid, vals, context)

        val = {}
        if 'default_code' in vals and not 'magento_sku' in vals:
            val['default_code'] = self.browse(cr, uid, product_id, context).default_code
            val['magento_sku'] = val['default_code']
            super(product_product, self).write(cr, uid, [product_id], val, context)

        return product_id

    def write(self, cr, uid, ids, vals, context=None):
        """Convert url key slug line"""

        result = True
        if not isinstance(ids, list):
            ids = [ids]

        for id in ids:
            # if 'magento_sku' in vals:
                # if self._check_magento_sku(cr, uid, vals['magento_sku'], id):
                    # raise osv.except_osv(_("Alert"), _("Error! Magento SKU %s must be unique") % (vals['magento_sku']))

            if 'magento_url_key' in vals:
                slug = slugify(unicode(vals['magento_url_key'], 'UTF-8'))
                vals['magento_url_key'] = slug

            result = result and super(product_product, self).write(cr, uid, [id], vals, context)

        return result

    def copy(self, cr, uid, id, default={}, context=None, done_list=[], local=False):
        """ 
        When copy, magento url key add -copy if exist magento_url_key
        """

        product = self.browse(cr, uid, id, context=context)
        if not default:
            default = {}
        if product.magento_url_key:
            default = default.copy()
            slug = product.magento_url_key
            while self.search(cr, uid, [('magento_url_key', '=', slug)]):
                slug += _('-copy')
            default['magento_url_key'] = slug
        if product.magento_sku:
            default['magento_sku'] = "%s-copy" % (product.magento_sku)
        return super(product_product, self).copy(cr, uid, id, default, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for val in self.browse(cr, uid, ids):
            if val.magento_exportable:
                raise osv.except_osv(_("Alert"), _("Product '%s' not allow to delete because are active in Magento Shop") % (val.name))
        return super(product_product, self).unlink(cr, uid, ids, context)

    def magento_create_product_type(self, cr, uid, magento_app, product, store_view, context):
        """Magento Create Product Type
        Get magento_create_product_TYPE def, where type is type of product
        Example: magento_create_product_configurable
        :magento_app object
        :product dicc
        :store_view Store View ID
        :return values
        """
        product_obj = self.pool.get('product.product')

        product_product = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.product', product['product_id'])
        if not product_product: #create
            if hasattr(product_obj, 'magento_create_product_' + product['type']):
                magento_create_product_type = getattr(product_obj, 'magento_create_product_' + product['type'])
                magento_create_product_type(cr, uid, magento_app, product, store_view, context)
            else:
                self.magento_create_product(cr, uid, magento_app, product, store_view, context)
        else:
            LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Skip! Product exists: magento %s, magento product id %s. Not create" % (magento_app.name, product['product_id']))

        return True

    def magento_create_product(self, cr, uid, magento_app, product, store_view, context=None):
        """Create Product from Magento Values
        :magento_app object
        :product dicc
        :store_view ID
        :return product_product_oerp_id
        """
        if context is None:
            context = {}

        values = self.magento_product_values(cr, uid, magento_app, product, context)
        if 'product_tmpl_id' in context:
            values['product_tmpl_id'] = context['product_tmpl_id']

        product_product_oerp_id = self.pool.get('product.product').create(cr, uid, values, context)
        self.pool.get('magento.external.referential').create_external_referential(cr, uid, magento_app, 'product.product', product_product_oerp_id, product['product_id'])
        LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Create Product Product: magento app %s, openerp id %s, magento product id %s." % (magento_app.name, product_product_oerp_id, product['product_id']))

        #~ Update product info
        with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
            product_info = product_api.info(int(product['product_id']), store_view)

        product_obj = self.pool.get('product.product').browse(cr, uid, product_product_oerp_id, context)

        context['magento_app'] = magento_app
        context['product_info'] = product_info
        product_product_vals = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.product', product_product_oerp_id, product_info, context)
        product_template_vals = self.pool.get('base.external.mapping').get_external_to_oerp(cr, uid, 'magento.product.template', product_obj.product_tmpl_id.id, product_info, context)
        vals = dict(product_product_vals, **product_template_vals)
        #~ print vals #dicc value to write
        self.pool.get('product.product').write(cr, uid, [product_product_oerp_id], vals)
        LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "Write Product Product: magento %s, openerp id %s, magento product id %s." % (magento_app.name, product_product_oerp_id, product['product_id']))

        cr.commit()

        return product_product_oerp_id

    def magento_product_values(self, cr, uid, magento_app, product, context=None):
        """Get Product Values from Magento Values
        Transform dicc by Base External Mapping
        :magento_app object
        :product dicc
        :return values
        """
        if context is None:
            context = {}

        external_referential_id = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.attributes.group', product['set'])
        attribute_external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [external_referential_id])

        category_ids = []
        if 'categories' in product:
            categories = product['categories']
        if 'category_ids' in product:
            categories = product['category_ids']
        if len(categories) > 0 and 'category_ids' in product:
            for cat_id in product['category_ids']:
                try:
                    category_id = self.pool.get('magento.external.referential').check_mgn2oerp(cr, uid, magento_app, 'product.category', cat_id)
                    external_referentials = self.pool.get('magento.external.referential').get_external_referential(cr, uid, [category_id])
                    category_ids.append(external_referentials[0]['oerp_id'])
                except:
                    continue

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

        if len(category_ids) > 0:
            values['categ_ids'] = [(6, 0, category_ids)]

        return values

product_product()
