"""
Update products from ID to ID Magento -> OpenERP
Use mapping external magento.product.product and magento.product.template
"""

import xmlrpclib
import optparse

from config import *

from magento import *

def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-f", "--from", dest="from_id",
                    default=False,
                    help="From ID")
    parser.add_option("-t", "--to", dest="to_id",
                    default=False,
                    help="From ID")
    options, args = parser.parse_args()

    if not options.from_id:
        print "From ID not available"
        return False
    if not options.to_id:
        print "To ID not available"
        return False

    from_id = int(options.from_id)
    to_id = int(options.to_id)+1

    url = 'http' + (secure and 's' or '') + '://' + server + ':' + port
    common = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
    uid = common.login(dbname, username, password)
    object = xmlrpclib.ServerProxy(url + '/xmlrpc/object')

    context = {}
    context['magento_app'] = MAGENTO_APP

    with Product(MGN_URL, MGN_APIUSER, MGN_APIPASSWORD) as product_api:
        for product_mgn_id in range(from_id,to_id):
            try:
                product_info = product_api.info(product_mgn_id)
            except:
                print "[SKIP] Magento ID %s NOT exists" % (product_mgn_id)
                continue
            print "[ID] %s" % (product_mgn_id)

            if not 'sku' in product_info:
                continue

            product_mgn_info = {}
            for key, value in product_info.iteritems():
                if value != None:
                    product_mgn_info[key] = value

            product_product_vals = object.execute(dbname, uid, password, 'base.external.mapping', 'get_external_to_oerp', 'magento.product.product', '', product_mgn_info, context)
            product_template_vals = object.execute(dbname, uid, password, 'base.external.mapping', 'get_external_to_oerp', 'magento.product.template', '', product_mgn_info, context)

            vals = dict(product_product_vals, **product_template_vals)
            args = [
                ('magento_sku','=',product_info['sku']),
            ]
            ids = object.execute(dbname, uid, password, 'product.product', 'search', args)

            if len(ids)>0:
                #~ for lang in LANGS:
                    #~ context['lang'] = lang
                result = object.execute(dbname, uid, password, 'product.product', 'write', ids, vals, context)
                print "[WRITE] Write product SKU %s ID %s" % (product_info['sku'], ids)
                #print vals
                print result
            else:
                print "[ALERT] Error write product SKU %s" % (product_info['sku'])

    return True

if __name__ == "__main__":
    main()


