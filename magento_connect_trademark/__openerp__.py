# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
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
    "name" : "Magento Connector - Trademark (Manufacturer)",
    "version" : "1.0",
    "author" : "Zikzakmedia SL",
    "website" : "www.zikzakmedia.com",
    "category" : "Generic Modules",
    "description": """
    Magento E-commerce Trademark management. Relation Manafacturer Magento availables in OpenERP Manafacturers.
    """,
    "license" : "AGPL-3",
    "depends" : [
        "magento_connect",
        "product_trademark",
    ],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "settings/magento_mapping.xml",
        "mgn_view.xml",
        "sale_view.xml",
    ],
    "active": False,
    "installable": True
}
