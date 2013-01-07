# -*- encoding: utf-8 -*-

from magento import ProductAttribute
from tools.translate import _
from osv import osv, fields
import time
import threading
import netsvc
import pooler


LOGGER = netsvc.Logger()

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    #TODO: make translations
    _columns = {
        'magento_last_export_trademark': fields.datetime('Last Export Trademarks', help='This date is last export. If you need export new manufacturers, you can modify this date (filter)'),
    }

    def magento_export_trademark(self, cr, uid, ids, context=None):
        """
        Sync Trademarks to Magento Site filterd by magento_sale_shop
        Get ids all trademarks and send one to one to Magento
        :return True
        """

        trademarks_shop_ids = []
        for shop in self.browse(cr, uid, ids):
            magento_app = shop.magento_website.magento_app_id
            last_exported_time = shop.magento_last_export_trademark

            # write sale shop date last export
            self.pool.get('sale.shop').write(cr, uid, shop.id, {'magento_last_export_trademark': time.strftime('%Y-%m-%d %H:%M:%S')})

            res_partner_trademarks_ids = self.pool.get('res.partner').search(cr, uid, [('manufacturer','=',True)])

            for res_partner_trademark in self.pool.get('res.partner').perm_read(cr, uid, res_partner_trademarks_ids):
                if last_exported_time < res_partner_trademark['create_date'][:19] or (res_partner_trademark['write_date'] and last_exported_time < res_partner_trademark['write_date'][:19]):
                    trademarks_shop_ids.append(res_partner_trademark['id'])

            if shop.magento_default_language:
                context['lang'] = shop.magento_default_language.code

            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Manufacturers to sync: %s" % (trademarks_shop_ids))

            context['shop'] = shop

            cr.commit()
            thread1 = threading.Thread(target=self.magento_export_trademarks_stepbystep, args=(cr.dbname, uid, magento_app.id, trademarks_shop_ids, context))
            thread1.start()

        return True

    def magento_export_trademarks_stepbystep(self, db_name, uid, magentoapp, ids, context=None):
        """
        Get all IDs trademarks to create in Magento
        :param dbname: str
        :magentoapp: int
        :saleshop: int
        :ids: list
        :return mgn_id
        """

        if len(ids) == 0:
            LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Trademarks Export")
            return True

        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()

        magento_manufacturer_obj = self.pool.get('magento.manufacturer')

        magento_app = self.pool.get('magento.app').browse(cr, uid, magentoapp)
        context['magento_app'] = magento_app
        manufacturer_name = magento_app.manufacturer_name


        magento_log_obj = self.pool.get('magento.log')
        request = []

        with ProductAttribute(magento_app.uri, magento_app.username, magento_app.password) as product_attribute_api:
            for trademark in self.pool.get('res.partner').browse(cr, uid, ids, context):
                LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "Waiting OpenERP ID %s...." % (trademark.id))
                mgn_id = magento_manufacturer_obj.search(cr, uid, [('manufacturer_id', '=', trademark.id),('magento_app_id','=',magento_app.id)])
                if mgn_id:
                    continue

                data = {'label':[{'store_id':[0,], 'value':trademark.name},]}

                try:
                    result = product_attribute_api.createOption(manufacturer_name, data)
                    if result:
                        options = product_attribute_api.options(manufacturer_name)
                        mgn_id = None
                        for option in options:
                            if option['label'] == trademark.name:
                                mgn_id = option['value']
                                break

                        if mgn_id:
                            vals = {
                                'magento_app_id': magento_app.id,
                                'manufacturer_id': trademark.id,
                                'value': mgn_id,
                                'label': trademark.name,
                                }
                            magento_manufacturer_obj.create(cr, uid, vals)
                            LOGGER.notifyChannel('Magento Attribute Manufacturer', netsvc.LOG_INFO, "Manufacturer %s create" % (trademark.id))
                            magento_log_obj.create_log(cr, uid, magento_app, 'magento.manufacturer', trademark.id, mgn_id, 'done', _('Successfully export trademark: %s') % (trademark.name) )
                        else:
                            raise Exception()
                    else:
                        raise Exception()
                except:
                    message = _('Error: Magento Tradename: %s. OpenERP ID: %s, Magento ID %s') % (trademark.name, trademark.id, mgn_id)
                    LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_ERROR, message)
                    magento_log_obj.create_log(cr, uid, magento_app, 'magento.manufacturer', trademark.id, mgn_id, 'error', message)
                    request.append(message)
                cr.commit()

        LOGGER.notifyChannel('Magento Sale Shop', netsvc.LOG_INFO, "End Trademarks Export")
        self.pool.get('magento.app').set_request(cr, uid, magento_app, request)
        cr.close()

        return True

    def run_export_trademark_scheduler(self, cr, uid, context=None):
        """Scheduler Catalog Trademark Cron"""
        self._sale_shop(cr, uid, self.magento_export_trademark, context=context)

sale_shop()
