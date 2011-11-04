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

class product_images(osv.osv):
    _inherit = "product.images"

    _columns = {
        'magento_exportable':fields.boolean('Magento Exportable'),
        'magento_base_image':fields.boolean('Base Image'),
        'magento_small_image':fields.boolean('Small Image'),
        'magento_thumbnail':fields.boolean('Thumbnail'),
        'magento_exclude':fields.boolean('Exclude'),
        'magento_position':fields.integer('Position'),
        'magento_app_ids':fields.many2many('magento.app', 'product_images_magento_app_rel', 'magento_app_id', 'product_images_id', 'Magento App'),
    }

    _defaults = {
        'magento_base_image':lambda * a:True,
        'magento_small_image':lambda * a:True,
        'magento_thumbnail':lambda * a:True,
        'magento_exclude':lambda * a:False
    }

    def create(self, cr, uid, values, context=None):
        """
        :values -> Dictionary with values
        :return id
        """
        if context is None:
            context = {}
        id = super(product_images, self).create(cr, uid, values, context)
        product_image_magento_app_obj = self.pool.get('product.image.magento.app')
        product_image = self.browse(cr, uid, id, context)
        if product_image.magento_exportable and len(values['magento_app_ids'][0][2]) > 0:
            for magento_app_id in values['magento_app_ids'][0][2]:
                vals = {
                    'product_image_id': id,
                    'magento_app_id': magento_app_id,
                }
                product_image_magento_app_obj.create(cr, uid, vals, context)
        return id

    #TODO: write -> product.image.magento.app
    def write(self, cr, uid, ids, values, context = None):
        """
        :values -> Dictionary with values
        :return true
        """
        if context is None:
            context = {}
        product_image_magento_app_obj = self.pool.get('product.image.magento.app')
        for product_image in self.browse(cr, uid, ids, context):
            if product_image.magento_exportable:
                product_image_magento_app_ids = product_image_magento_app_obj.search(cr, uid, [
                    ('product_image_id', 'in', ids),
                ], context = context)
                if len(product_image_magento_app_ids) > 0:
                    product_image_magento_app_obj.unlink(cr, uid, product_image_magento_app_ids, context)
                for magento_app_id in values['magento_app_ids'][0][2]:
                    vals = {
                        'product_image_id': product_image.id,
                        'magento_app_id': magento_app_id,
                    }
                    product_image_magento_app_obj.create(cr, uid, vals, context)
        super(product_images, self).write(cr, uid, ids, values, context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_("Alert"), _("This Image can't be deleted"))

product_images()

class product_images_magento_app(osv.osv):
    _name = 'product.images.magento.app'
    _description = 'Product Images related with Magento App'

    _columns = {
        'product_image_id': fields.many2one('product.images', 'Product Image', required=True),
        'magento_app_id': fields.many2one('magento.app', 'Magento App', required=True),
    }

product_images_magento_app()

