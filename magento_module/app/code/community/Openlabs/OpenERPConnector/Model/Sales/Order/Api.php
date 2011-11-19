<?php

class Openlabs_OpenERPConnector_Model_Sales_Order_Api extends Mage_Sales_Model_Order_Api {
	
	public function retrieveOrders($data) {
			        
	    $result = array();
		if(isset($data['imported'])) {
			$billingAliasName = 'billing_o_a';
	        $shippingAliasName = 'shipping_o_a';
	        
	        $collection = Mage::getModel("sales/order")->getCollection()
	            ->addAttributeToSelect('*')
	            ->addAttributeToFilter('imported', array('eq' => $data['imported']))
	            ->addAddressFields()
	            ->addExpressionFieldToSelect(
	                'billing_firstname', "{{billing_firstname}}", array('billing_firstname'=>"$billingAliasName.firstname")
	            )
	            ->addExpressionFieldToSelect(
	                'billing_lastname', "{{billing_lastname}}", array('billing_lastname'=>"$billingAliasName.lastname")
	            )
	            ->addExpressionFieldToSelect(
	                'shipping_firstname', "{{shipping_firstname}}", array('shipping_firstname'=>"$shippingAliasName.firstname")
	            )
	            ->addExpressionFieldToSelect(
	                'shipping_lastname', "{{shipping_lastname}}", array('shipping_lastname'=>"$shippingAliasName.lastname")
	            )
	            ->addExpressionFieldToSelect(
	                    'billing_name',
	                    "CONCAT({{billing_firstname}}, ' ', {{billing_lastname}})",
	                    array('billing_firstname'=>"$billingAliasName.firstname", 'billing_lastname'=>"$billingAliasName.lastname")
	            )
	            ->addExpressionFieldToSelect(
	                    'shipping_name',
	                    'CONCAT({{shipping_firstname}}, " ", {{shipping_lastname}})',
	                    array('shipping_firstname'=>"$shippingAliasName.firstname", 'shipping_lastname'=>"$shippingAliasName.lastname")
	            );
	            
	        if(isset($data['limit'])) {
	        	$collection->setPageSize($data['limit']);
	        	$collection->setOrder('entity_id', 'ASC');
	        }
	        
	        if(isset($data['filters']) && is_array($data['filters'])) {
	        	$filters = $data['filters'];
	        	foreach($filters as $field => $value) {
	        		$collection->addAttributeToFilter($field, $value);
	        	}
	        }

	        foreach ($collection as $order) {
	            $result[] = $this->_getAttributes($order, 'order');
	        }
	        return $result;
		}else{
			$this->_fault('data_invalid', "erreur, l'attribut 'imported' doit être spécifié");
		}
	}
	
	public function setFlagForOrder($incrementId) {
		$_order = $this->_initOrder($incrementId);
		$_order->setImported(1);
		try {
			$_order->save();
			return true;
		} catch (Mage_Core_Exception $e) {
            $this->_fault('data_invalid', $e->getMessage());
        }
	}
	
	/* Récupère l'increment_id de la commande fille créée, retourne un string exemple : 100004997-1 */
    public function getOrderChild($incrementId) {
    	
        $order = Mage::getModel('sales/order')->loadByIncrementId($incrementId);
        /**
          * Check order existing
          */
        if (!$order->getId()) {
             $this->_fault('order_not_exists');
        }
        
        if($order->getRelationChildId()) {
        	return $order->getRelationChildRealId();
        }else{
        	return false;
        }
    }
    
    /* Récupère l'increment_id de la commande mère annulée, retourne un string exemple : 100004997 */
    public function getOrderParent($incrementId) {
    	
    	$order = Mage::getModel('sales/order')->loadByIncrementId($incrementId);
        /**
          * Check order existing
          */
        if (!$order->getId()) {
             $this->_fault('order_not_exists');
        }
        
        if($order->getRelationParentId()) {
        	return $order->getRelationParentRealId();
        }else{
        	return false;
        }
    }
}