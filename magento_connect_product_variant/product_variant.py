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
LOGGER = netsvc.Logger()

class product_variant_dimension_type(osv.osv):
    _inherit = "product.variant.dimension.type"

    _columns = {
        'code':fields.char('Code', size=100),
    }

    def unlink(self, cr, uid, ids, context=None):
        """Not allow delete this type if was mapping by Magento"""
        types = self.pool.get('magento.external.referential').search(cr, uid, [('oerp_id','in',ids),('model_id.model', '=', 'product.variant.dimension.type')])
        if len(types)>0:
            raise osv.except_osv(_("Alert"), _("This Magento Product Dimension Type not allow to delete"))

        return super(product_variant_dimension_type, self).unlink(cr, uid, ids, context)

    def magento_dimension_type(self, cr, uid, magento_app, type_name, magento_id):
        """Create Product Dimension Type:  Color, Size
        One OpenERP Dimension Type = Multi Magento Dimension Type
        :magento_app object
        :type_name str
        :magento_id ID
        :return dimesion_type ID
        """
        mgn_external_referential = self.pool.get('magento.external.referential')

        dimension_type = self.search(cr, uid, [('code','=',type_name)])
        if len(dimension_type) == 0:
            values = {
                'name': type_name,
                'code': type_name,
                'mandatory_dimension': True,
            }
            dimension_type = self.create(cr, uid, values)
            LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "New Dimension Type: %s." % (type_name))
        else:
            dimension_type = dimension_type[0]

        # Add Magento External Referential
        type = mgn_external_referential.check_mgn2oerp(cr, uid, magento_app, 'product.variant.dimension.type', magento_id)
        if not type:
            mgn_external_referential.create_external_referential(cr, uid, magento_app, 'product.variant.dimension.type', dimension_type, magento_id)

        return dimension_type

product_variant_dimension_type()


class product_variant_dimension_option(osv.osv):
    _inherit = "product.variant.dimension.option"

    def unlink(self, cr, uid, ids, context=None):
        """Not allow delete this option if was mapping by Magento"""
        types = self.pool.get('magento.external.referential').search(cr, uid, [('oerp_id','in',ids),('model_id.model', '=', 'product.variant.dimension.option')])
        if len(types)>0:
            raise osv.except_osv(_("Alert"), _("This Magento Product Dimension Option not allow to delete"))

        return super(product_variant_dimension_option, self).unlink(cr, uid, ids, context)

    def magento_dimension_option(self, cr, uid, magento_app, dimension_id, dimension_options):
        """Create Product Dimension Option: XL, L, Blue, Red
        One OpenERP Dimension Option = Multi Magento Dimension Option
        :magento_app object
        :dimension_id Dimesion ID
        :dimension_options list {'value': '', 'label': ''}
        :return dimension_options_ids list  IDs
        """
        mgn_external_referential = self.pool.get('magento.external.referential')

        dimension_options_ids = []
        for dimension_option in dimension_options:
            dimension_name = dimension_option['label']
            dimension_magneto_id = dimension_option['value']
            if dimension_name:
                dimesion_option = self.search(cr, uid, [('name','=',dimension_name),('dimension_id','=',dimension_id)])
                if len(dimesion_option) == 0:
                    values = {
                        'name': dimension_name,
                        'code': dimension_name,
                        'dimension_id': dimension_id,
                    }
                    dimesion_option_id = self.create(cr, uid, values)
                    LOGGER.notifyChannel('Magento Sync API', netsvc.LOG_INFO, "New Dimension Option: %s." % (dimension_name))
                else:
                    dimesion_option_id = dimesion_option[0]

                dimension_options_ids.append(dimesion_option_id)

                # Add Magento External Referential
                option = mgn_external_referential.check_mgn2oerp(cr, uid, magento_app, 'product.variant.dimension.option', dimension_magneto_id)
                if not option:
                    mgn_external_referential.create_external_referential(cr, uid, magento_app, 'product.variant.dimension.option', dimesion_option_id, dimension_magneto_id)
            
        return dimension_options_ids

product_variant_dimension_option()
