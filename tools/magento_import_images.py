import xmlrpclib
import optparse

from config import *

url = 'http' + (secure and 's' or '') + '://' + server + ':' + port
common = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
uid = common.login(dbname, username, password)
object = xmlrpclib.ServerProxy(url + '/xmlrpc/object')


def main():

    context = {}
    ids = [MAGENTO_APP] #magento.app
    result = object.execute(dbname, uid, password, 'magento.app', 'core_sync_images', ids, context)
    print result

if __name__ == "__main__":
    main()

