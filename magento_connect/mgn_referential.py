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

class magento_external_referential(osv.osv):
    _name = 'magento.external.referential'
    _description = 'Magento External Referential'
    _rec_name = 'magento_app_id'

    _columns = {
        'magento_app_id': fields.many2one('magento.app', 'Magento App', required=True),
        'model_id': fields.many2one('ir.model', 'OpenERP Model', required=True, select=True, ondelete='cascade'),
        'oerp_id': fields.integer('OpenERP ID', required=True),
        'mgn_id': fields.integer('Magento ID', required=True),
    }
    
    def unlink(self, cr, uid, vals, context=None):
        raise osv.except_osv(_("Alert"), _("This External mapping not allow to delete"))
        
    def get_external_referential(self, cr, uid, ids):
        """
        Get values external referential
        :param ids: list
        :return external_referentials: list[dicc]
        """
        external_referentials = []
        for values in self.browse(cr, uid, ids):
            values = {
                'magento_app_id': values.magento_app_id.id,
                'model_id': values.model_id.id,
                'oerp_id': values.oerp_id,
                'mgn_id': values.mgn_id,
            }
            external_referentials.append(values)

        return external_referentials

    def get_mgnreferential_ids(self, cr, uid, magento_app, model, mgn_ids):
        """
        Get ID OpenERP from external referential ID
        :param magento_app: object
        :param model: str
        :param mgn_ids: list
        :return oerp_ids: list[ID]
        """
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])
        oerp_ids = []
        for mgn_id in mgn_ids:
            oerp_id = self.search(cr, uid, [('magento_app_id','=',magento_app.id),('model_id','=',model_ids[0]),('mgn_id','=',mgn_id)])
            if len(oerp_id)>0:
                oerp_ids.append(oerp_id[0])

        return oerp_ids

    def create_external_referential(self, cr, uid, magento_app, model, oerp_id, mgn_id):
        """
        Create new external referential
        :param magento_app: object
        :param model: str name model
        :param oerp_id: int OpenERP ID
        :param mgn_id: int Magento ID
        :return magento_external_referential_id
        """
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])

        values = {
            'magento_app_id': magento_app.id,
            'model_id': model_ids[0],
            'oerp_id': oerp_id,
            'mgn_id': mgn_id,
        }
        magento_external_referential_id = self.create(cr, uid, values)

        return magento_external_referential_id
            
    def check_mgn2oerp(self, cr, uid, magento_app, model, mgn_id):
        """
        Search if magento app, model and magento ID exists in other syncronizations
        :param magento_app: object
        :param model: str name model
        :param mgn_id: int Magento ID
        :return id or False
        """
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])
        values = self.search(cr, uid, [('magento_app_id','=',magento_app.id),('model_id','=',model_ids[0]),('mgn_id','=',mgn_id)])

        if len(values)>0:
            return values[0]
        else:
            return False

    def check_oerp2mgn(self, cr, uid, magento_app, model, oerp_id):
        """
        Search if magento app, model and openerp ID exists in other syncronizations
        :param magento_app: object
        :param model: str name model
        :param oerp_id: int OpenERP ID
        :return id or False
        """
        model_ids = self.pool.get('ir.model').search(cr, uid, [('model','=',model)])
        values = self.search(cr, uid, [('magento_app_id','=',magento_app.id),('model_id','=',model_ids[0]),('oerp_id','=',oerp_id)])

        if len(values)>0:
            return values[0]
        else:
            return False

magento_external_referential()
