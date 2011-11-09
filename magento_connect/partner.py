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
import netsvc

from magento import *

class res_partner(osv.osv):
    _inherit = "res.partner"

    _columns = {
        'magento_app_customer': fields.one2many('magento.app.customer', 'partner_id', 'Magento Customer'),
    }

    def magento_create_partner(self, cr, uid, ids, magento_app, values, context = None):
        """Create Partner from Magento Values
        Transform dicc by Base External Mapping
        :return partner_id
        """

        logger = netsvc.Logger()

        magento_vat = values['taxvat']
        external_referential_obj = self.pool.get('magento.external.referential')

        vat = False
        if magento_vat:
            country_obj = self.pool.get('res.country')
            country_id = country_obj.search(cr, uid, [('code', 'ilike', magento_vat[:2])], context = context)
            if len(country_id) == 0: # The VAT has not a valid country code
                partner_address_obj = self.pool.get('res.partner.address')
                country_code = partner_address_obj.magento_get_customer_address_country_code(cr, uid, ids, magento_app, values, context)
                vat = '%s%s' % (country_code, magento_vat)
            else: # The VAT has a valid country code
                vat = magento_vat
            if hasattr(self, 'check_vat_' + vat[:2].lower()):
                check = getattr(self, 'check_vat_' + vat[:2].lower())
                vat_ok = check(vat[2:])
            if vat_ok:
                values['vat'] = vat.upper()
                """If already exist a partner with the same VAT, skip it"""
                partner_id = self.search(cr, uid, [('vat', '=', values['vat'] )], context = context)
                if len(partner_id) > 0:
                    return partner_id[0]

        context['magento_app'] = magento_app
        values['name'] = '%s %s' % (values['firstname'], values['lastname'])
        res_partner_vals_obj = self.pool.get('base.external.mapping')
        res_partner_vals = res_partner_vals_obj.get_external_to_oerp(cr, uid, 'magento.res.partner', False, values, context)
        res_partner_vals['customer'] = True #fix this partner is customer
        partner_id = self.create(cr, uid, res_partner_vals, context)
        external_referential_obj.create_external_referential(cr, uid, magento_app, 'res.partner', partner_id, values['customer_id'])

        logger.notifyChannel('Magento Sync Partner', netsvc.LOG_INFO, "Create Partner: magento %s, openerp id %s, magento id %s" % (magento_app.name, partner_id, values['customer_id']))

        return partner_id

res_partner()

class res_partner_address(osv.osv):
    _inherit = "res.partner.address"

    _columns = {
        'magento_firstname':fields.char('First Name', size=100),
        'magento_lastname':fields.char('Last Name', size=100),
    }

    def magento_get_customer_address_country_code(self, cr, uid, ids, magento_app, customer, context = None):
        """Get Country Code Customer Billing Address
        :magento_app: object
        :customer: dicc
        :return str country_code
        """

        customer_addresses = self.magento_get_customer_address(cr, uid, ids, magento_app, customer, context)
        for customer_address in customer_addresses:
            country_code = customer_address['country_id']
            while not customer_address['is_default_billing']:
                continue
            break
        return country_code

    def magento_get_customer_address(self, cr, uid, ids, magento_app, customer, context = None):
        """Get Country Code Customer Billing Address
        :magento_app: object
        :customer: dicc
        :return list customer_addresses
        """

        with CustomerAddress(magento_app.uri, magento_app.username, magento_app.password) as customer_address_api:
            customer_addresses = []
            for customer_address in customer_address_api.list(customer['customer_id']):
                customer_addresses.append(customer_address)
        return customer_addresses

    def magento_create_partner_address(self, cr, uid, ids, magento_app, partner_id, values, context = None):
        """Create Partner Address from Magento Values
        Transform dicc by Base External Mapping
        :magento_app: object
        :values: [dicc]
        :partner_id ID
        :return partner_address_ids. List address ids
        """

        logger = netsvc.Logger()

        external_referential_obj = self.pool.get('magento.external.referential')
        base_external_mapping_obj = self.pool.get('base.external.mapping')
        country_obj = self.pool.get('res.country')
        state_obj = self.pool.get('res.country.state')

        partner_address_ids = []
        vals = {}
        for customer_address in self.magento_get_customer_address(cr, uid, ids, magento_app, values, context):
            vals['name'] = '%s %s' % (customer_address['firstname'], customer_address['lastname'])
            vals['city'] = customer_address['city']
            vals['phone'] = customer_address['telephone']
            vals['street'] = customer_address['street']
            vals['zip'] = customer_address['postcode']
            vals['magento_firstname'] = customer_address['firstname']
            vals['magento_lastname'] = customer_address['lastname']
            vals['email'] = values['email']
            vals['partner_id'] = partner_id
            vals['type'] =  customer_address['is_default_billing'] and 'invoice' or customer_address['is_default_shipping'] and 'delivery' or 'default'
            country_ids = country_obj.search(cr, uid, [('code', '=', customer_address['country_id'])], context = context)
            vals['country_id'] = country_ids and country_ids[0] or False
            state_ids = state_obj.search(cr, uid, [('name', '=', customer_address['region'])], context = context)
            vals['state_id'] = state_ids and state_ids[0] or False

            partner_address_vals = base_external_mapping_obj.get_external_to_oerp(cr, uid, 'magento.res.partner.address', False, vals, context)
            partner_address_id = self.create(cr, uid, partner_address_vals, context)
            external_referential_obj.create_external_referential(cr, uid, magento_app, 'res.partner.address', partner_address_id, customer_address['customer_address_id'])

            logger.notifyChannel('Magento Sync Partner Address', netsvc.LOG_INFO, "Create Partner Address: magento %s, openerp id %s, magento id %s" % (magento_app.name, partner_address_id, customer_address['customer_address_id']))

            partner_address_ids.append(partner_address_id)

        return partner_address_ids

res_partner_address()
