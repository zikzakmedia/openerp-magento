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

from osv import osv, fields
from tools.translate import _
import netsvc

class res_partner(osv.osv):
    _inherit = "res.partner"

    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            magento_manufacturer = self.pool.get('magento.manufacturer').search(cr, uid, [('manufacturer_id', '=', id)])
            if magento_manufacturer:
                raise osv.except_osv(_("Alert"), _("Partner ID '%s' not allow to delete because are active in Magento Manafacturer") % (id))
        return super(res_partner, self).unlink(cr, uid, ids, context)

res_partner()
