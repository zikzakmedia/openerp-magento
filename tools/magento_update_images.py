"""
Update product images from Magento -> OpenERP
"""

import xmlrpclib
import optparse

from config import *

from magento import *
from ooop import OOOP

def main():
    url = 'http' + (secure and 's' or '') + '://' + server
    o = OOOP(user=username,pwd=password,dbname=dbname,uri=url,port=port)

    url = 'http' + (secure and 's' or '') + '://' + server + ':' + port
    common = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
    uid = common.login(dbname, username, password)
    object = xmlrpclib.ServerProxy(url + '/xmlrpc/object')

    print dbname
    context = {}
    context['magento_app'] = MAGENTO_APP

    with ProductImages(MGN_URL, MGN_APIUSER, MGN_APIPASSWORD) as product_image_api:
        args = [('magento_exportable','=',True)]
        product_ids = object.execute(dbname,uid,password,'product.product','search',args)
        print len(product_ids)

        for product_id in product_ids:
            args = [('oerp_id','=',product_id),('model_id','=',109)]
            product = object.execute(dbname,uid,password,'magento.external.referential','search',args)
            if len(product) > 0:
                prod = object.execute(dbname,uid,password,'magento.external.referential','read',product,['mgn_id','oerp_id'])
                try:
                    product_images = product_image_api.list(prod[0]['mgn_id'])
                    for product_image in product_images:
                        if 'url' in product_image: #magento == 1.3
                            url = product_image['url']
                        else: #magento < 1.5
                            url = product_image['filename']

                        splited_url = url.split('/')
                        filename = splited_url[len(splited_url)-1]

                        imgs = o.ProductImages.filter(filename=filename)

                        for i in imgs:
                            if product_image['exclude'] == '1':
                                i.magento_exclude = True
                            else:
                                i.magento_exclude = False
                            if 'image' in product_image['types']:
                                i.magento_base_image = True
                            else:
                                i.magento_base_image = False 
                            if 'small_image' in product_image['types']:
                                i.magento_small_image = True
                            else:
                                i.magento_small_image = False
                            if 'thumbnail' in product_image['types']:
                                i.magento_thumbnail = True
                            else:
                                i.magento_thumbnail = False 

                            i.save()
                            print "[UPDATE] %s Mgn - Image filename %s" % (prod[0]['mgn_id'],filename)
                        
                except:
                    print "[ALERT] Not update images %s" % (prod[0]['mgn_id'])
                    continue

    return True

if __name__ == "__main__":
    main()


