# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
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

from magento import *

LOGGER = netsvc.Logger()

class magento_app(osv.osv):
    _inherit = 'magento.app'
    _description = 'Magento Server - APP'

    _columns = {
        'manufacturer_name': fields.char('Manufacturer', size=256, help='Manufacturer attribute name'),
    }

    _defaults = {
        'manufacturer_name': 'manufacturer',
    }

    def core_sync_attributes_manafacturer(self, cr, uid, ids, context):
        """
        def sync Manufacturer Magento to OpenERP
        Only create new values if not exist; not update or delete
        :ids list magento app
        :return True
        """

        partner_obj = self.pool.get('res.partner')
        magento_manufacturer_obj = self.pool.get('magento.manufacturer')

        for magento_app in self.browse(cr, uid, ids):
            with ProductAttribute(magento_app.uri, magento_app.username, magento_app.password) as  product_attribute_api:
                manufacturer = magento_app.manufacturer_name or 'manufacturer'
                try:
                    attribute_options = product_attribute_api.options(manufacturer)
                except:
                    raise osv.except_osv(_("Alert"), _("Not exist manufacturer attribute"))

                for option in attribute_options:
                    partner_id = False

                    #check  if manufacturer attribute exists in magento.manufacturer
                    manufacturer_ids = magento_manufacturer_obj.search(cr, uid, [
                                            ('magento_app_id','=',magento_app.id),
                                            ('value','=', option['value']),
                                            ])
                    if len(manufacturer_ids)>0:
                        LOGGER.notifyChannel('Magento Attribute Manufacturer', netsvc.LOG_ERROR, "Skip! Manufacturer %s exists magento APP %s" % (option['label'],  magento_app.name))
                        continue

                    #search manufacturer name to relation m2n or create new
                    partner_ids = partner_obj.search(cr, uid, [
                                            ('name','=',option['label']),
                                            ('manufacturer','=', True),
                                            ])
                    if len(partner_ids)>0:
                        partner_id = partner_ids[0]
                    else:
                        if option.get('value',False):
                            vals = {
                                'name': option['label'],
                                'manufacturer': True,
                            }
                            partner_id = partner_obj.create(cr, uid, vals)

                    if not partner_id:
                        LOGGER.notifyChannel('Magento Attribute Manufacturer', netsvc.LOG_ERROR, "Manufacturer %s not create partner ID" % (option['label']))
                        continue

                    #create new manufacturer
                    if option.get('value',False):
                        vals = {
                            'magento_app_id': magento_app.id,
                            'manufacturer_id': partner_id,
                            'value': option['value'],
                            'label': option['label'],
                        }
                        magento_manufacturer_obj.create(cr, uid, vals)
                        LOGGER.notifyChannel('Magento Attribute Manufacturer', netsvc.LOG_INFO, "Manufacturer %s create partner %s" % (option['label'], partner_id))

        return True

magento_app()

class magento_manufacturer(osv.osv):
    _name = 'magento.manufacturer'
    _description = 'Magento manufacturer'

    _rec_name = 'manufacturer_id'

    _columns = {
        'magento_app_id': fields.many2one('magento.app','Magento App', required=True),
        'manufacturer_id': fields.many2one('res.partner', 'Manufacturer', required=True),
        'value': fields.char('ID', size=64, required=True),
        'label': fields.char('Label', size=64, required=True),
    }

magento_manufacturer()
