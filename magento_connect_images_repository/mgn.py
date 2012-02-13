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

from magento import *

import netsvc
import time
import urllib2
import os

LOGGER = netsvc.Logger()

class magento_app(osv.osv):
    _inherit = 'magento.app'

    def core_sync_images(self, cr, uid, ids, context):
        """
        def sync Images from Magento to OpenERP. 
        Add only file name in database (not url) and save image in company directory
        Only create new values if not exist; not update or delete
        :ids list
        :return True
        """

        magento_external_referential_obj = self.pool.get('magento.external.referential')
        product_image_magento_app_obj = self.pool.get('product.images.magento.app')
        product_images_obj = self.pool.get('product.images')

        for magento_app in self.browse(cr, uid, ids):
            with Product(magento_app.uri, magento_app.username, magento_app.password) as product_api:
                magento_external_referential_ids = magento_external_referential_obj.search(cr, uid, [('model_id.model', '=', 'product.product'), ('magento_app_id', 'in', [magento_app.id])], context = context)
                product_ids = magento_external_referential_obj.read(cr, uid, magento_external_referential_ids, ['oerp_id', 'mgn_id'], context)

                with ProductImages(magento_app.uri, magento_app.username, magento_app.password) as product_image_api:
                    for product_id in product_ids:
                        LOGGER.notifyChannel('Magento Sync Images', netsvc.LOG_INFO, "Check Magento ID %s images..." % (product_id['mgn_id']))
                        for product_image in product_image_api.list(product_id['mgn_id']):
                            image_ids = product_images_obj.search(cr, uid, [('filename', '=', product_image['url'])], context = context)
                            if len(image_ids) > 0:
                                product_image_magento_ids = product_image_magento_app_obj.search(cr, uid, [('magento_app_id', '=', magento_app.id), ('product_images_id', 'in', image_ids)], context=context)
                                if len(product_image_magento_ids) > 0: #exist
                                    LOGGER.notifyChannel('Magento Sync Images', netsvc.LOG_INFO, "Image skipped! Image for this product in this Magento App already exists. Not created.")
                                    continue

                            name = product_image['label']
                            if 'url' in product_image: #magento == 1.3
                                url = product_image['url']
                            else: #magento < 1.5
                                url = product_image['filename']

                            splited_url = url.split('/')
                            filename = splited_url[len(splited_url)-1]

                            if not name:
                                name = filename

                            exclude = False
                            if product_image['exclude'] == '1':
                                exclude = True

                            base_image = False
                            small_image = False
                            thumbnail = False
                            if 'image' in product_image['types']:
                                base_image = True
                            if 'small_image' in product_image['types']:
                                small_image = True
                            if 'thumbnail' in product_image['types']:
                                thumbnail = True

                            vals = {
                                'name': name,
                                'link': True,
                                'filename': filename,
                                'magento_base_image':base_image,
                                'magento_small_image':small_image,
                                'magento_thumbnail':thumbnail,
                                'magento_exclude': exclude,
                                'magento_position': product_image['position'],
                                'product_id': product_id['oerp_id'],
                                'magento_filename': name,
                                'magento_exportable': True,
                                'magento_app_ids': [(6, 0, [magento_app.id])],
                            }

                            #download image and save image
                            local_media_repository = magento_app.warehouse_id.company_id.local_media_repository
                            
                            if not local_media_repository:
                                LOGGER.notifyChannel('Magento Sync Images', netsvc.LOG_ERROR, "Configure Company Media Repository")
                                return False

                            try:
                                out = os.path.join(local_media_repository,filename)
                                f = urllib2.urlopen(url)
                                open(out,"wb").write(f.read())
                            except:
                                LOGGER.notifyChannel('Magento Sync Images', netsvc.LOG_ERROR, "Error dowload file from %s. Not create image" % (url))
                                continue

                            product_images_id =  product_images_obj.create(cr, uid, vals, context)
                            prod_image_mgn_app_ids = product_image_magento_app_obj.search(cr, uid, [('product_images_id','=',product_images_id),('magento_app_id','=',magento_app.id)])
                            if len(prod_image_mgn_app_ids)>0:
                                product_image_magento_app_obj.write(cr, uid, prod_image_mgn_app_ids, {'magento_exported':True})

                            cr.commit()
                            LOGGER.notifyChannel('Magento Sync Images', netsvc.LOG_INFO, " Magento %s, Image %s created, Product ID %s" % (magento_app.name, name, product_id['oerp_id']))

        LOGGER.notifyChannel('Magento Sync Images', netsvc.LOG_INFO, " End Import Images from %s" % (magento_app.name))

        return True


magento_app()
