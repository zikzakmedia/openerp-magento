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

LOGGER = netsvc.Logger()

class res_partner(osv.osv):
    _inherit = "res.partner"

    _columns = {
        'magento_app_customer': fields.one2many('magento.app.customer', 'partner_id', 'Magento Customer'),
    }

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            order = self.pool.get('magento.external.referential').search(cr, uid, [('model_id.model', '=', 'res.partner'), ('oerp_id', '=', id)])
            if order:
                raise osv.except_osv(_("Alert"), _("Partner ID '%s' not allow to delete because are active in Magento") % (id))
        return super(res_partner, self).unlink(cr, uid, ids, context)
    
    def magento_customer_info(self, magento_app, customer_id):
        """Get info Magento Customer
        :magento_app object
        :return customer
        """
        with Customer(magento_app.uri, magento_app.username, magento_app.password) as customer_api:
            customer = customer_api.info(customer_id)

        return customer

    def magento_create_partner(self, cr, uid, magento_app, values, mapping = True, context = None):
        """Create Partner from Magento Values
        Transform dicc by Base External Mapping
        :return partner_id
        """
        if context is None:
            context = {}

        vat = False
        vat_ok = False
        magento_vat = values.get('taxvat')

        external_referential_obj = self.pool.get('magento.external.referential')
        res_partner_vals_obj = self.pool.get('base.external.mapping')

        if magento_vat:
            country_obj = self.pool.get('res.country')
            country_id = country_obj.search(cr, uid, [('code', 'ilike', magento_vat[:2])], context = context)

            if len(country_id) == 0: # The VAT has not a valid country code
                partner_address_obj = self.pool.get('res.partner.address')
                country_code = partner_address_obj.magento_get_customer_address_country_code(cr, uid, magento_app, values, context)
                vat = '%s%s' % (country_code, magento_vat)
            else: # The VAT has a valid country code
                vat = magento_vat

            if hasattr(self, 'check_vat_' + vat[:2].lower()):
                check = getattr(self, 'check_vat_' + vat[:2].lower())
                vat_ok = check(vat[2:])

            if vat_ok:
                values['vat'] = vat.upper()
                """If already exist a partner with the same VAT:
                Create External Referential
                Return partner_id
                """
                partner_id = self.search(cr, uid, [('vat', '=', values['vat'] )], context = context)
                if len(partner_id) > 0:
                    external_referential_obj.create_external_referential(cr, uid, magento_app, 'res.partner', partner_id[0], values['customer_id'])
                    return partner_id[0]

        context['magento_app'] = magento_app
        values['name'] = '%s %s' % (values['firstname'].title(), values['lastname'].title())
        res_partner_vals = res_partner_vals_obj.get_external_to_oerp(cr, uid, 'magento.res.partner', False, values, context)
        res_partner_vals['customer'] = True #fix this partner is customer
        partner_id = self.create(cr, uid, res_partner_vals, context)

        if mapping and ('customer_id' in values):
            external_referential_obj.create_external_referential(cr, uid, magento_app, 'res.partner', partner_id, values['customer_id'])
            self.pool.get('magento.log').create_log(cr, uid, magento_app, 'res.partner', partner_id, values['customer_id'], 'done', _('Successfully create partner: %s') % (values['name']) )
        else:
            self.pool.get('magento.log').create_log(cr, uid, magento_app, 'res.partner', partner_id, '', 'done', _('Successfully create partner: %s') % (values['name']) )

        magento_app_customer_ids = self.pool.get('magento.app.customer').magento_app_customer_create(cr, uid, magento_app, partner_id, values, context)

        LOGGER.notifyChannel('Magento Sync Partner', netsvc.LOG_INFO, "Create Partner: magento %s, openerp id %s, magento id %s" % (magento_app.name, partner_id, values['customer_id']))

        return partner_id

    def get_mapped_partners(self, cr, uid, magento_app, context = None):
        """Get mapped partners of OpenERP with Magento
        :magento_app: Browse object of magento_app model
        :return Partner list of magento_external_referential's browse objects
        """
        if context is None:
            context = {}
        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model', '=', 'res.partner')], context = context)[0]

        extern_ref_obj = self.pool.get('magento.external.referential')
        extern_ref_ids = extern_ref_obj.search(cr, uid, [
            ('magento_app_id','=', magento_app.id),
            ('model_id','=', model_id),
        ], context = context)
        return extern_ref_obj.browse(cr, uid, extern_ref_ids, context)

    def magento_get_name(self, cr, uid, partner, context = None):
        """Split the name of the partner into magento_firstname and magento_lastname
        :partner: Partner browse object
        :return: dictionary with magento_firstname and magento_lastname values for customer
        """
        if context is None:
            context = {}
        result = {}
        partner_name = partner.name.split(' ')

        if len(partner_name)>3:
            result['firstname'] = ' '.join(partner_name[:2])
            partner_name.remove(partner_name[0])
        else:
            result['firstname'] = ''.join(partner_name[:1])
        partner_name.remove(partner_name[0])

        result['lastname'] = ' '.join(partner_name[:])
        if result['lastname'] == '': #not empty
            result['lastname'] = '--'

        return result

res_partner()

class res_partner_address(osv.osv):
    _inherit = "res.partner.address"

    _columns = {
        'magento_firstname':fields.char('First Name', size=100),
        'magento_lastname':fields.char('Last Name', size=100),
    }

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            order = self.pool.get('magento.external.referential').search(cr, uid, [('model_id.model', '=', 'res.partner.address'), ('oerp_id', '=', id)])
            if order:
                raise osv.except_osv(_("Alert"), _("Partner Address ID '%s' not allow to delete because are active in Magento") % (id))
        return super(res_partner_address, self).unlink(cr, uid, ids, context)

    def magento_customer_address_info(self, magento_app, customer_address_id):
        """Get info Magento Customer
        :magento_app object
        :return customer
        """
        with CustomerAddress(magento_app.uri, magento_app.username, magento_app.password) as customer_address_api:
            try:
                address = customer_address_api.info(customer_address_id)
            except:
                return False

        return address

    def magento_get_customer_address_country_code(self, cr, uid, magento_app, customer, context = None):
        """Get Country Code Customer Billing Address
        :magento_app: object
        :customer: dicc
        :return str country_code
        """
        if context is None:
            context = {}

        customer_addresses = self.magento_get_customer_address(cr, uid, magento_app, customer, context)
        country_code = False
        for customer_address in customer_addresses:
            country_code = customer_address['country_id']
            if 'is_default_billing' in customer_address:
                break
        return country_code

    def magento_get_customer_address(self, cr, uid, magento_app, customer, context = None):
        """Get Country Code Customer Billing Address
        :magento_app: object
        :customer: dicc
        :return list customer_addresses
        """
        if context is None:
            context = {}

        with CustomerAddress(magento_app.uri, magento_app.username, magento_app.password) as customer_address_api:
            customer_addresses = []
            for customer_address in customer_address_api.list(customer['customer_id']):
                customer_addresses.append(customer_address)
        return customer_addresses

    def magento_partner_address_data(self, cr, uid, customer_address, context):
        """Partner Address Data.
        Transform dicc by Base External Mapping
        Remember add email in customer_address dicc
        :customer_address: dicc
        :return partner_address_vals
        """

        base_external_mapping_obj = self.pool.get('base.external.mapping')
        country_obj = self.pool.get('res.country')
        mgn_region_obj = self.pool.get('magento.region')

        vals = {}
        vals['name'] = '%s %s' % (customer_address['firstname'].title(), customer_address['lastname'].title())
        vals['city'] = customer_address['city'].title()
        vals['phone'] = customer_address['telephone']
        street = customer_address['street'].title()
        street = street.replace(unicode('º','UTF-8'), '')
        street = street.replace(unicode('ª','UTF-8'), '')
        vals['street'] = street
        vals['zip'] = customer_address['postcode']
        vals['magento_firstname'] = customer_address['firstname']
        vals['magento_lastname'] = customer_address['lastname']
        if 'email' in customer_address:
            vals['email'] = customer_address['email']
        country_ids = country_obj.search(cr, uid, [('code', '=', customer_address['country_id'])], context = context)
        vals['country_id'] = country_ids and country_ids[0] or False
        if 'region_id' in customer_address:
            state_ids = mgn_region_obj.search(cr, uid, [('region_id', '=', customer_address['region_id'])], context = context)
            if state_ids:
                magento_region = mgn_region_obj.browse(cr, uid, state_ids[0])
                vals['state_id'] = magento_region.res_country_state_id.id
        partner_address_vals = base_external_mapping_obj.get_external_to_oerp(cr, uid, 'magento.res.partner.address', False, vals, context)
        
        return partner_address_vals

    def magento_create_partner_address(self, cr, uid, magento_app, partner_id, customer_address, mapping = True, type = 'default', context = None):
        """Create Partner Address from Magento Values
        :magento_app: object
        :partner_id: ID
        :customer_address: [dicc]
        :mapping: True/False
        :type: default, invoice, delivery
        :return partner_address_id
        """
        if context is None:
            context = {}

        external_referential_obj = self.pool.get('magento.external.referential')

        partner_address_vals = self.magento_partner_address_data(cr, uid, customer_address, context)
        partner_address_vals['partner_id'] = partner_id
        partner_address_vals['type'] =  type

        """Adding Company Name of Billing address like Partner Name"""
        if type == 'invoice' or type == 'default':
            if customer_address.get('company') and customer_address.get('company') != None:
                LOGGER.notifyChannel('Magento', netsvc.LOG_INFO, 'Change Partner name: %s (company)' % customer_address.get('company'))
                self.pool.get('res.partner').write(cr,uid,[partner_id],{'name':customer_address['company']}, context)

        partner_address_id = self.create(cr, uid, partner_address_vals, context)
        if mapping and ('customer_address_id' in customer_address):
            external_referential_obj.create_external_referential(cr, uid, magento_app, 'res.partner.address', partner_address_id, customer_address['customer_address_id'])

        if 'customer_address_id' in customer_address:
            LOGGER.notifyChannel('Magento Sync Partner Address', netsvc.LOG_INFO, "Create Partner Address: magento %s, openerp id %s, magento id %s" % (magento_app.name, partner_address_id, customer_address['customer_address_id']))
            self.pool.get('magento.log').create_log(cr, uid, magento_app, 'res.partner.address', partner_address_id, customer_address['customer_address_id'], 'done', _('Successfully create partner address: %s') % (partner_address_vals['name']) )
        else:
            LOGGER.notifyChannel('Magento Sync Partner Address', netsvc.LOG_INFO, "Create Partner Address: magento %s, openerp id %s, %s" % (magento_app.name, partner_address_id, partner_address_vals['name']))
            self.pool.get('magento.log').create_log(cr, uid, magento_app, 'res.partner.address', partner_address_id, '', 'done', _('Successfully create partner address: %s') % (partner_address_vals['name']) )

        return partner_address_id

    def magento_update_partner_address(self, cr, uid, magento_app, partner_address_id, customer_address, context):
        """Update Partner Address from Magento Values
        :magento_app: object
        :partner_address_id: ID
        :customer_address: [dicc]
        :return partner_address_id
        """
        if context is None:
            context = {}

        partner_address_vals = self.magento_partner_address_data(cr, uid, customer_address, context)

        try:
            self.write(cr, uid, [partner_address_id], partner_address_vals, context)
            LOGGER.notifyChannel('Magento Sync Partner Address', netsvc.LOG_INFO, "Update Partner Address: magento %s, openerp id %s" % (magento_app.name, partner_address_id))
            self.pool.get('magento.log').create_log(cr, uid, magento_app, 'res.partner.address', partner_address_id, customer_address['customer_address_id'], 'done', _('Successfully update partner address: %s') % (partner_address_vals['name']) )
        except:
            LOGGER.notifyChannel('Magento Sync Partner Address', netsvc.LOG_ERROR, "Update Partner Address: magento %s, openerp id %s" % (magento_app.name, partner_address_id))
            self.pool.get('magento.log').create_log(cr, uid, magento_app, 'res.partner.address', partner_address_id, customer_address['customer_address_id'], 'error', _('Error update partner address: %s') % (partner_address_vals['name']) )

        return partner_address_id

    def magento_ghost_customer_address(self, cr, uid, magento_app, partner_id, customer_id, values, type = 'default', context = None):
        """If Create Partner same time create order, Magento Customer Address ID = 0
        1- Check zip and address exists in Address OpenERP
        2- Get Customer API. Check Address. Not mapping address
        3- Not address available. Create Address Order
        :magento_app: object
        :partner_id: ID Partner
        :customer_id: ID Customer
        :values: dicc
        :return: openerp address ID
        """
        create_ghost_address = True
        zip = values['postcode']
        street = values['street']

        """Adding Company Name of Billing address like Partner Name"""
        if type == 'invoice' or type == 'default':
            if values.get('company') and values.get('company') != None:
                LOGGER.notifyChannel('Magento', netsvc.LOG_INFO, 'Change Partner name: %s (company)' % values.get('company'))
                self.pool.get('res.partner').write(cr,uid,[partner_id],{'name':values['company']}, context)

        address = self.pool.get('res.partner.address').search(cr, uid, [
                ('zip','=',zip),
                ('street','=',street),
                ('partner_id','=',partner_id),
            ])
    
        if len(address)>0:
            return address[0]
        else:
            with CustomerAddress(magento_app.uri, magento_app.username, magento_app.password) as customer_address_api:
                customer_address = customer_address_api.list(customer_id)
                for address in customer_address:
                    if address['postcode'] == zip and address['street'] == street:
                        create_ghost_address = False
                        return self.magento_create_partner_address(cr, uid, magento_app, partner_id, address, mapping = True)
                if len(customer_address)>0:
                    return self.magento_create_partner_address(cr, uid, magento_app, partner_id, customer_address[0], mapping = False)
                else:
                    customer_address = {}
                    customer_address['firstname'] = values['firstname']
                    customer_address['lastname'] = values['lastname']
                    customer_address['city'] = values['city']
                    customer_address['telephone'] = values['telephone']
                    customer_address['street'] = values['street']
                    customer_address['postcode'] = values['postcode']
                    customer_address['email'] = values['email']
                    customer_address['country_id'] = values['country_id']
                    customer_address['region_id'] = values['region_id']
                    return self.magento_create_partner_address(cr, uid, magento_app, partner_id, customer_address, mapping = False)


    def magento_get_address_name(self, cr, uid, partner_address, context = None):
        """Split the name of the partner into magento_firstname and magento_lastname
        :partner_address: Partner address browse object
        :return: dictionary with magento_firstname and magento_lastname values for customer address
        """
        if context is None:
            context = {}
        result = {}

        if partner_address.magento_firstname:
            firstname = partner_address.magento_firstname
        else:
            if partner_address.name:
                partner_name = partner_address.name.split(' ')
            else:
                partner_name = partner_address.partner_id.name.split(' ')
            if len(partner_name)>3:
                firstname = ' '.join(partner_name[:2])
                partner_name.remove(partner_name[0])
            else:
                firstname = ''.join(partner_name[:1])
            partner_name.remove(partner_name[0])
        result['firstname'] = firstname.title()

        if partner_address.magento_lastname:
            lastname = partner_address.magento_lastname
        else:
            lastname = ' '.join(partner_name)

        result['lastname'] = lastname.title()
        if result['lastname'] == '': #not empty
            result['lastname'] = '--'

        return result

res_partner_address()
