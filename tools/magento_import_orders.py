import xmlrpclib
import optparse

from config import *

url = 'http' + (secure and 's' or '') + '://' + server + ':' + port
common = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
uid = common.login(dbname, username, password)
object = xmlrpclib.ServerProxy(url + '/xmlrpc/object')


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

    context = {}

    context['ofilter'] = {'entity_id':{'from':options.from_id, 'to':options.to_id}}

    print context

    result = object.execute(dbname, uid, password, 'sale.shop', 'magento_import_orders', SALE_SHOP, context)
    print result

if __name__ == "__main__":
    main()
