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

class product_images_magento_app(osv.osv):
    _name = 'product.images.magento.app'
    _description = 'Product Images related with Magento App'

    _columns = {
        'product_images_id': fields.many2one('product.images', 'Product Image', required=True),
        'magento_app_id': fields.many2one('magento.app', 'Magento App', required=True),
        'magento_exported':fields.boolean('Exported to Magento?'),
    }

product_images_magento_app()

class product_images(osv.osv):
    _inherit = "product.images"

    _columns = {
        'magento_exportable':fields.boolean('Magento Exportable'),
        'magento_base_image':fields.boolean('Base Image'),
        'magento_small_image':fields.boolean('Small Image'),
        'magento_thumbnail':fields.boolean('Thumbnail'),
        'magento_exclude':fields.boolean('Exclude'),
        'magento_position':fields.integer('Position'),
        'magento_app_ids':fields.many2many('magento.app', 'product_images_magento_app', 'product_images_id', 'magento_app_id', 'Magento App'),
        'magento_filename': fields.char('Magento File Name', size=128, readonly=True),
    }

    _defaults = {
        'magento_base_image':lambda * a:True,
        'magento_small_image':lambda * a:True,
        'magento_thumbnail':lambda * a:True,
        'magento_exclude':lambda * a:False
    }

    def write(self, cr, uid, ids, values, context=None):
        """
        :values -> Dictionary with values
        :return true
        """

        #If edit product form, lose magento_exported field. Not same at product.image edit form
        if 'magento_app_ids' in values:
            prod_img_mgn_app_obj = self.pool.get('product.images.magento.app')

            prod_img_mgn_app_ids = prod_img_mgn_app_obj.search(cr, uid, [('product_images_id','in',ids)])
            prod_img_mgn_app_exported = prod_img_mgn_app_obj.read(cr, uid, prod_img_mgn_app_ids, ['magento_exported'])
        
        super(product_images, self).write(cr, uid, ids, values, context)

        if 'magento_app_ids' in values:
            #add new values in order list search
            if len(prod_img_mgn_app_exported)>0:
                keys = []
                for prod_img_mgn_app_id in prod_img_mgn_app_obj.search(cr, uid, [('product_images_id','in',ids)]):
                    keys.append(prod_img_mgn_app_id)

                values = []
                for prod_exported in prod_img_mgn_app_exported:
                    values.append(prod_exported['magento_exported'])
                
                for val in zip(keys, values):
                    prod_img_mgn_app_exported = prod_img_mgn_app_obj.write(cr, uid, [val[0]], {'magento_exported':val[1]})

        return True

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Image can't be deleted"))

product_images()
