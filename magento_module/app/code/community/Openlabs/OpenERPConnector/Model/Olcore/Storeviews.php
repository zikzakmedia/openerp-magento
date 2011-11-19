<?php

/**
 * @author Sharoon Thomas
 * Inspired from Dieter's Magento Extender
 * @copyright 2009
 */

class Openlabs_OpenERPConnector_Model_Olcore_Storeviews extends Mage_Catalog_Model_Api_Resource
{
        public function items($filters=null)
        {
            try
            {
            $collection = Mage::getModel('core/store')->getCollection();//->addAttributeToSelect('*');
            }
            catch (Mage_Core_Exception $e)
            {
               $this->_fault('store_not_exists');
            }
            
            if (is_array($filters)) {
                try {
                    foreach ($filters as $field => $value) {
                        $collection->addFieldToFilter($field, $value);
                    }
                } catch (Mage_Core_Exception $e) {
                    $this->_fault('filters_invalid', $e->getMessage());
                    // If we are adding filter on non-existent attribute
                }
            }

            $result = array();
            foreach ($collection as $customer) {
                $result[] = $customer->toArray();
            }

            return $result;
        }

	public function info($storeIds = null)
	{
		$stores = array();

		if(is_array($storeIds))
		{
			foreach($storeIds as $storeId)
			{
				try
                                {
                                    $stores[] = Mage::getModel('core/store')->load($storeId)->toArray();
				}
                                catch (Mage_Core_Exception $e)
                                {
                                    $this->_fault('store_not_exists');
                                }
                        }
                        return $stores;
		}
                elseif(is_numeric($storeIds))
		{
			try
                        {
                            return Mage::getModel('core/store')->load($storeIds)->toArray();
			}
                        catch (Mage_Core_Exception $e)
                        {
                            $this->_fault('store_not_exists');
                        }

                }
		
        }

        public function create($storedata)
        {
            try
            {
                $store = Mage::getModel('core/store')
                    ->setData($storedata)
                    ->save();

            }
            catch (Magento_Core_Exception $e)
            {
                $this->_fault('data_invalid',$e->getMessage());
            }
            catch (Exception $e)
            {
                $this->_fault('data_invalid',$e->getMessage());
            }
            return $store->getId();
        }

        public function update($storeid,$storedata)
        {
            try
            {
                $store = Mage::getModel('core/store')
                    ->load($storeid);
                if (!$store->getId())
                {
                    $this->_fault('store_not_exists');
                }
                $store->addData($storedata)->save();
            }
            catch (Magento_Core_Exception $e)
            {
                $this->_fault('data_invalid',$e->getMessage());
            }
            catch (Exception $e)
            {
                $this->_fault('data_invalid',$e->getMessage());
            }
            return true;
        }

        public function delete($storeid)
        {
            try
            {
                $store = Mage::getModel('core/store')
                    ->load($storeid);
                if (!$store->getId())
                {
                    $this->_fault('store_not_exists');
                }
                $store->delete();

            }
            catch (Magento_Core_Exception $e)
            {
                $this->_fault('data_invalid',$e->getMessage());
            }
            catch (Exception $e)
            {
                $this->_fault('data_invalid',$e->getMessage());
            }
            return true;
        }
}
?>
