<?php
/**
 * Magento
 *
 * NOTICE OF LICENSE
 *
 * This source file is subject to the Open Software License (OSL 3.0)
 * that is bundled with this package in the file LICENSE.txt.
 * It is also available through the world-wide-web at this URL:
 * http://opensource.org/licenses/osl-3.0.php
 * If you did not receive a copy of the license and are unable to
 * obtain it through the world-wide-web, please send an email
 * to license@magentocommerce.com so we can send you a copy immediately.
 *
 * DISCLAIMER
 *
 * Do not edit or add to this file if you wish to upgrade Magento to newer
 * versions in the future. If you wish to customize Magento for your
 * needs please refer to http://www.magentocommerce.com for more information.
 *
 * @category   Mage
 * @package    Mage_Customer
 * @copyright  Copyright (c) 2008 Irubin Consulting Inc. DBA Varien (http://www.varien.com)
 * @license    http://opensource.org/licenses/osl-3.0.php  Open Software License (OSL 3.0)
 */

/**
 * Customer address api
 *
 * @category   Mage
 * @package    Mage_Customer
 * @author     Magento Core Team <core@magentocommerce.com>
 */
class Openlabs_OpenERPConnector_Model_Olcustomer_Subscriber extends Mage_Customer_Model_Api_Resource
{
    protected $_mapAttributes = array(
        'customer_id' => 'entity_id'
    );

    public function __construct()
    {
        $this->_ignoredAttributeCodes[] = 'parent_id';
    }

    /**
     * Retrive subscriber list
     *
     * @param int $filters
     * @return array
     */
    public function items($filters=null)
    {
        $collection = Mage::getModel('customer/customer')->getCollection()
            ->addAttributeToSelect('*');


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
            $subscriber = Mage::getModel('newsletter/subscriber')->loadByEmail($customer['email']);
            if($subscriber->getId())
                $result[] = $subscriber->getId();
        }

        return $result;
    }

    /**
     * Create new address for customer
     *
     * @param int $customerId
     * @param array $email
     * @return int
     */
    public function create($customerId,$email)
    {
        if($customerId && $email):
            $customer = Mage::getModel("newsletter/subscriber");

            $customer->setCustomerId($customerId);
            $customer->setEmail($email);
            $customer->subscriber_status = "1";

            $customer->save();

            return $customer->getId();
        else:
            return False;
        endif;
    }

    /**
     * Retrieve subscriber data
     *
     * @param int $subscriberId
     * @return array
     */
    public function info($subscriberId)
    {
        $subscriber = Mage::getModel('newsletter/subscriber')->load($subscriberId);

        if($subscriber->getId()):
                $result[] = $subscriber->toArray();
        endif;

        return $result;
    }

    /**
     * Update subscriber data (subscriber)
     *
     * @param $email
     * @return boolean
     */
    public function update($email)
    {
        if($email):
            $subscriber = Mage::getModel('newsletter/subscriber')->loadByEmail($email);

            if($subscriber->getId()):
                $customer = Mage::getModel("newsletter/subscriber")->load($subscriber->getId());
                $customer->subscriber_status = "1";
                $customer->save();
            endif;

            return $subscriber->getId();
        else:
            return False;
        endif;
    }

    /**
     * Delete subscriber (unsubscriber)
     *
     * @param $email
     * @return boolean
     */
    public function delete($email)
    {
        if($email):
            $subscriber = Mage::getModel('newsletter/subscriber')->loadByEmail($email);

            if($subscriber->getId()):
                Mage::getModel('newsletter/subscriber')->load($subscriber->getId())->unsubscribe();
            endif;

            return $subscriber->getId();
        else:
            return False;
        endif;
    }
} // Class Mage_Customer_Model_Address_Api End
