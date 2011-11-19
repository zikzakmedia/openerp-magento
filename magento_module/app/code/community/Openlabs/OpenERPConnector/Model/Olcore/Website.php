<?php

/**
 * @author Sharoon Thomas
 * Inspired from Dieter's Magento Extender
 * @copyright 2009
 */

class Openlabs_OpenERPConnector_Model_Olcore_Website extends Mage_Catalog_Model_Api_Resource
{

	public function items($filters=null)
        {
            try
            {
            $collection = Mage::getModel('core/website')->getCollection();//->addAttributeToSelect('*');
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
                                    $stores[] = Mage::getModel('core/website')->load($storeId)->toArray();
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
                            return Mage::getModel('core/website')->load($storeIds)->toArray();
			}
                        catch (Mage_Core_Exception $e)
                        {
                            $this->_fault('store_not_exists');
                        }

                }

        }
	//This is a protected function used by items & info for fetching website information
	
	public function create($websitedata)
        {
            try
            {
                $website = Mage::getModel('core/website')
                    ->setData($websitedata)
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
            return $website->getId();
        }

        public function update($websiteid,$websitedata)
        {
            try
            {
                $website = Mage::getModel('core/website')
                    ->load($websiteid);
                if (!$website->getId())
                {
                    $this->_fault('website_not_exists');
                }
                $website->addData($websitedata)->save();
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

        public function delete($websiteid)
        {
            try
            {
                $website = Mage::getModel('core/website')
                    ->load($websiteid);
                if (!$website->getId())
                {
                    $this->_fault('website_not_exists');
                }
                $website->delete();
                
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
        
	public function tree()
	{
		$tree = array();
		
		$websites = $this->websites();
		
		foreach($websites as $website)
		{
			$groups = $this->groups($website['group_ids']);	
			$tree[$website['code']] = $website;
			foreach($groups as $group)
			{
				$stores = $this->stores($group["store_ids"]);
				
				$tree[$website['code']]['groups']['group_'.$group['group_id']] = $group;
				
				foreach($stores as $store)
				{
					$tree[$website['code']]['groups']['group_'.$group['group_id']]['stores'][$store['code']] = $store;
				}
			}
		}

		return $tree;
	}
	
}
?>