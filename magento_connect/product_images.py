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
        'magento_base_image':fields.boolean('Base Image'),
        'magento_small_image':fields.boolean('Small Image'),
        'magento_thumbnail':fields.boolean('Thumbnail'),
        'magento_exclude':fields.boolean('Exclude'),
        'magento_position':fields.integer('Position'),
    }

    _defaults = {
        'magento_base_image':lambda * a:True,
        'magento_small_image':lambda * a:True,
        'magento_thumbnail':lambda * a:True,
        'magento_exclude':lambda * a:False
    }

product_images()
