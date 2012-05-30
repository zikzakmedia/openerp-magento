from magento import *
from config import *

import xmlrpclib
import optparse

"""
Check IDs products from Magento are available in OpenERP (exist magento external referential)
Edit id_from and id_to range IDs to check
Print list IDs not availables
"""
#edit this lines
id_from = 1 #ID magneto start check
id_to = 1 #ID magento finish check

oerpurl = 'http' + (secure and 's' or '') + '://' + server + ':' + port
common = xmlrpclib.ServerProxy(oerpurl + '/xmlrpc/common')
uid = common.login(dbname, username, password)
object = xmlrpclib.ServerProxy(oerpurl + '/xmlrpc/object')

res = []

for i in range(id_from, id_to):
    with Product(MGN_URL, MGN_APIUSER, MGN_APIPASSWORD) as product_api:
        ofilter = {'entity_id': i}
        product = product_api.list(ofilter)
        if len(product) > 0:
            product = product[0]
            if product['type'] == 'simple':
                mgn_id = int(product['product_id'])
                result = object.execute(dbname, uid, password, 'magento.external.referential', 'search', [('magento_app_id','=',MAGENTO_APP),('model_id','=',115),('mgn_id','=',mgn_id)])
                if not result:
                    print "No create %s" % mgn_id
                    res.append(mgn_id)

print res
