<?php


/**
 * @author Sharoon Thomas
 * Inspired from Dieter's Magento Extender
 * @copyright 2009
 */

class Openlabs_OpenERPConnector_Model_Olcatalog_Product_Attribute extends Mage_Catalog_Model_Api_Resource {
	public function __construct() {
		$this->_storeIdSessionField = 'product_store_id';
		$this->_ignoredAttributeCodes[] = 'type_id';
		$this->_ignoredAttributeTypes[] = 'gallery';
		$this->_ignoredAttributeTypes[] = 'media_image';
	}

	/**
	 * Retrieve attributes from specified attribute set
	 *
	 * @param int $setId
	 * @return array
	 */
	public function relations($setId){
		$attributes = Mage :: getModel('catalog/product')->getResource()->loadAllAttributes()->getSortedAttributes($setId);
		$result = array ();
		foreach ($attributes as $attribute){
			$result[] = Array(
						'attribute_id' => $attribute->getId()
							);
		}
		return $result;
		
	}
	public function items($setId) {
		$attributes = Mage :: getModel('catalog/product')->getResource()->loadAllAttributes()->getSortedAttributes($setId);
		$result = array ();

		foreach ($attributes as $attribute) {
			/* @var $attribute Mage_Catalog_Model_Resource_Eav_Attribute */
			if ((!$attribute->getId() || $attribute->isInSet($setId)) && $this->_isAllowedAttribute($attribute)) {

				if (!$attribute->getId() || $attribute->isScopeGlobal()) {
					$scope = 'global';
				}
				elseif ($attribute->isScopeWebsite()) {
					$scope = 'website';
				} else {
					$scope = 'store';
				}

				/*$result[] = array (
					'attribute_id' => $attribute->getId(),
					'code' => $attribute->getAttributeCode(),
					'type' => $attribute->getFrontendInput(),
					'required' => $attribute->getIsRequired(),
					'attributeset' => $attribute->getattribute_set_info(),
					'scope' => $scope
				);*/
				//Override hooray
				$attribute['scope'] = $scope;
				$result[]=$attribute->toArray();
			}
		}

		return $result;
	}

	public function info($attributeId) {
		try {
			return 'hello';
			$attribute = Mage :: getModel('catalog/product')->getResource()->getAttribute($attributeId);
			return $attribute->toArray();
		} catch (Exception $e) {
			$this->_fault('not_exists');
		}
	}
	/**
	 * Retrieve attribute options
	 *
	 * @param int $attributeId
	 * @param string|int $store
	 * @return array
	 */
	public function options($attributeId, $store = null) {
		$storeId = $this->_getStoreId($store);
		$attribute = Mage :: getModel('catalog/product')->setStoreId($storeId)->getResource()->getAttribute($attributeId)->setStoreId($storeId);

		/* @var $attribute Mage_Catalog_Model_Entity_Attribute */
		if (!$attribute) {
			$this->_fault('not_exists');
		}

		$options = array ();
			foreach ($attribute->getSource()->getAllOptions() as $optionId => $optionValue) {
				if (is_array($optionValue)) {
					$options[] = $optionValue;
				} 
				else {
					$options[] = array (
						'value' => $optionId,
						'label' => $optionValue
					);
				}
		}
		return $options;
	}
}
?>
