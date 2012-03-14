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

{
    "name" : "Magento Connector",
    "version" : "1.0",
    "author" : "Zikzakmedia SL",
    "website" : "www.zikzakmedia.com",
    "category" : "Generic Modules",
    "description": """
    Magento E-commerce management. Your Magento and OpenERP are connecting.

    1. Requirements:
     1.1 Install Magento Python from:
        - https://github.com/zikzakmedia/magento

     1.2 Install Magento Module Extend API. This module is same magentoerpconnect module use. Add additional API methods for use by the Multi website, Multi Store, Multi Product category 
        - https://github.com/zikzakmedia/magento_webservices

    2. Configuration
     2.1 Exclude product fields Magento go to OpenERP in Sale -> Configuration -> Magento Attribute Exclude
     2.2 Mapping more product fields go to Administrator -> Customization -> Database Structure -> External Mapping
     2.3 Configure yours Magento APP: Sale -> Configuration -> Magento
    
    3. Other information
     3.1 Magento module use Product Attributes to add new fields Product model. This module don't use EAV (Entity-attribute-value model) and there are maxim fields available in product table postgres.
     3.2 Also exists another module Magento management we working another projects:
        - https://launchpad.net/magentoerpconnect
        
    Documentation available at (spanish):
    http://wiki.zikzakmedia.com/openerp:magentoconnect

    Special Thanks to Akretion www.akretion.com and OpenLabs www.openlabs.co.in
    """,
    "license" : "AGPL-3",
    "depends" : [
        "account_payment_extension",
        "base_external_mapping",
        "base_vat",
        "delivery",
        "product_attributes",
        "product_m2mcategories",
        "product_images_olbs",
        "sale_margin",
        "sale_payment",
    ],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "settings/magento_attribute_exclude.xml",
        "settings/magento_mapping.xml",
        "settings/magento_category_attribute.xml",
        "settings/magento_data.xml",
        "mgn_view.xml",
        "mgn_referential_view.xml",
        "product_view.xml",
        "product_attributes_view.xml",
        "product_images_view.xml",
        "sale_view.xml",
        "partner_view.xml",
        "delivery_view.xml",
        "wizard/wizard_product_product.xml",
        "wizard/wizard_product_stock.xml",
        "wizard/wizard_product_price.xml",
        "wizard/wizard_product_images.xml",
    ],
    "active": False,
    "installable": True
}
