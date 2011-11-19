<?php


/**
 * @author Sharoon Thomas
 * Inspired from Dieter's Magento Extender
 * @copyright 2009
 */

class Openlabs_OpenERPConnector_Model_Olcatalog_Product_Attributegroup extends Mage_Catalog_Model_Api_Resource {
	public function olditems($setId = null) {
		$groups = Mage :: getModel('eav/entity_attribute_group')->getResourceCollection();

		if (!is_null($setId) && !empty ($setId) && is_numeric($setId)) {
			$groups->setAttributeSetFilter($setId);
		}

		$groups->load();

		$arrGroups = array ();

		foreach ($groups as $group) {
			$arrGroups[] = array (
				'attribute_group_id' => $group->getAttributeGroupId(),
				'attribute_set_id' => $group->getAttributeSetId(),
				'attribute_group_name' => $group->getAttributeGroupName(),
				'sort_order' => $group->getSortOrder(),
				'default_id' => $group->getDefaultId()
			);
		}

		return $arrGroups;
	}

	public function items($filters = null) {
		try {
			$collection = Mage :: getModel('eav/entity_attribute_group')->getCollection();
		} catch (Mage_Core_Exception $e) {
			$this->_fault('group_not_exists');
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

		$result = array ();
		foreach ($collection as $collection_item) {
			$result[] = $collection_item->toArray();
		}

		return $result;

	}
	/*
	<param><value><string>cl19t0dqhmheafqc0ccdeejc76</string></value></param>
	<param><value><string>catalog_product_attribute_group.create</string></value></param>
	<param>
		<value>
			<array>
				<data>
					<value><i4>26</i4></value>
					<value><string>Leonelle</string></value>
				</data>
			</array>
		</value>
	</param>
	*/
	public function create($setId, array $data) {
		try {
			// $attrOption = Mage_Eav_Model_Entity_Attribute_Group
			$attrOption = Mage :: getModel("eav/entity_attribute_group");

			$attrOption->addData($data);

			// check if there already exists a group with the give groupname
			if ($attrOption->itemExists()) {
				$this->_fault("group_already_exists");
			}

			$attrOption->save();

			return (int) $attrOption->getAttributeGroupId();
		} catch (Exception $ex) {
			return false;
		}
	}
	/*
	<param><value><string>cl19t0dqhmheafqc0ccdeejc76</string></value></param>
	<param><value><string>catalog_product_attribute_group.update</string></value></param>
	<param>
		<value>
			<array>
				<data>
					<value><i4>85</i4></value>
					<value><string>Leonelle2</string></value>
					<value><i4>85</i4></value>
					<value><i4>85</i4></value>
				</data>
			</array>
		</value>
	</param>
	*/
	public function update(array $data) {
		try {
			// $attrOption = Mage_Eav_Model_Entity_Attribute_Group
			$attrOption = Mage :: getModel("eav/entity_attribute_group");

			$attrOption->load($data["attribute_group_id"]);

			// check if the requested group exists...
			if (!$attrOption->getAttributeGroupId()) {
				$this->_fault("group_not_exists");
			}

			$attrOption->addData($data);

			$attrOption->save();

			return true;
		} catch (Exception $ex) {
			return false;
		}
	}

	/*
	<param><value><string>cl19t0dqhmheafqc0ccdeejc76</string></value></param>
	<param><value><string>catalog_product_attribute_group.delete</string></value></param>
	<param>
		<value>
			<array>
				<data>
					<value><i4>85</i4></value>
				</data>
			</array>
		</value>
	</param>
	*/
	public function delete($groupId) {
		try {
			// $attrOption = Mage_Eav_Model_Entity_Attribute_Group
			$attrOption = Mage :: getModel("eav/entity_attribute_group");

			$attrOption->load($groupId);

			// check if the requested group exists...
			if (!$attrOption->getAttributeGroupId()) {
				$this->_fault("group_not_exists");
			}

			// save data
			$attrOption->delete();

			return true;
		} catch (Exception $ex) {
			return false;
		}
	}

}
?>
