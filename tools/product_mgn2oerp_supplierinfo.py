from magento import *
from config import *

import xmlrpclib
import optparse

"""
Add suppliers from Magento to OpenERP (exist magento external referential)
Edit id_from and id_to range IDs to check
Print list IDs not availables
"""
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

    oerpurl = 'http' + (secure and 's' or '') + '://' + server + ':' + port
    common = xmlrpclib.ServerProxy(oerpurl + '/xmlrpc/common')
    uid = common.login(dbname, username, password)
    object = xmlrpclib.ServerProxy(oerpurl + '/xmlrpc/object')

    for i in range(int(options.from_id), int(options.to_id)):
        with Product(MGN_URL, MGN_APIUSER, MGN_APIPASSWORD) as product_api:
            ofilter = {'entity_id': i}
            product = product_api.list(ofilter)

            if len(product) > 0:
                product = product[0]
                if product['type'] == 'simple':
                    mgn_id = int(product['product_id'])
                    result = object.execute(dbname, uid, password, 'magento.external.referential', 'search', [('magento_app_id','=',MAGENTO_APP),('model_id','=',115),('mgn_id','=',mgn_id)])

                    if result: #product exist
                        try:
                            product = product_api.info(mgn_id)
                        except:
                            print "[ERROR] Product %s info" % (mgn_id)
                            continue

                        supplier = product[supplier_field]
                        
                        mgn_referential = object.execute(dbname, uid, password, 'magento.external.referential', 'read', [result[0]], ['oerp_id'])
                        product_id = mgn_referential[0]['oerp_id']
                        product_info = object.execute(dbname, uid, password, 'product.product', 'read', [product_id], ['product_tmpl_id'])
                        product_template_id = product_info[0]['product_tmpl_id'][0]

                        product_supplier = object.execute(dbname, uid, password, 'product.supplierinfo', 'search', [('product_id','=',product_template_id)])

                        if len(product_supplier) > 0:
                            print "[SKIP] Product %s, Template %s have supplier" % (product_id, product_template_id)
                            continue

                        if supplier:
                            supplier = supplier.title()

                            partners = object.execute(dbname, uid, password, 'res.partner', 'search', [('name','ilike',supplier)])

                            if len(partners) > 0:
                                partner = partners[0]
                                part = object.execute(dbname, uid, password, 'res.partner', 'write', [partner], {'supplier':True})
                            else:
                                partner = object.execute(dbname, uid, password, 'res.partner', 'create', {'name':supplier,'supplier':True})

                            values = {
                                'name': partner, #many2one
                                'product_id': product_template_id, #product_template
                                'min_qty': 1,
                                'delay': 1,
                            }
                            product_supplier = object.execute(dbname, uid, password, 'product.supplierinfo', 'create', values)
                            print "[ADD] Magento %s. Supplier %s in Product %s, Template %s" % (mgn_id, supplier, product_id, product_template_id)

                            try:
                                cost_price = float(product[cost_field])
                                values = {
                                    'suppinfo_id': product_supplier,
                                    'min_quantity': 1.0, #product_template
                                    'price': cost_price,
                                }
                                prod = object.execute(dbname, uid, password, 'pricelist.partnerinfo', 'create', values)
                                print "[ADD] Price %s Supplier %s in Product %s, Template %s" % (cost_price, supplier, product_id, product_template_id)
                            except:
                                print "[ERROR] Price Supplier %s in Product %s, Template %s" % (supplier, product_id, product_template_id)

    print "[OK!] Finish script"

if __name__ == "__main__":
    main()
