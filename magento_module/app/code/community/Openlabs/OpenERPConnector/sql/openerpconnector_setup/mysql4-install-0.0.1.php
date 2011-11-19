<?php
$installer = $this;
$installer->startSetup();

// Les noms des tables ont changé depuis la version 1.4.1.0
// avant la  1.4.1.0 			--> sales_order
// la 1.4.1.0 et celles d'après --> sales_flat_order

/* Récupère la version de magento*/
$version = Mage::getVersion();

$version = str_replace('.','',$version);
if($version>=1410)
	$tableName='sales_flat_order';
else
	$tableName='sales_order';

$db = $installer->getConnection();

/* Suppression */
if($db->tableColumnExists($this->getTable($tableName), 'imported')) {
	$installer->run("ALTER TABLE {$this->getTable($tableName)} drop column imported");
}

/* re-création */
if(!$db->tableColumnExists($this->getTable($tableName), 'imported')) {
	$installer->run("
		ALTER TABLE {$this->getTable($tableName)} ADD imported tinyint(1) unsigned NOT NULL default '0';
	");
}


/* Fin */
$installer->endSetup();