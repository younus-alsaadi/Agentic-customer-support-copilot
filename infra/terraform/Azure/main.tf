locals {
  rg_name = coalesce(var.resource_group_name, "${var.cluster_name}-rg")

  #  2 public + 2 private subnets
  subnet_map = {
    "public-1"  = var.public_subnets[0]
    "public-2"  = var.public_subnets[1]
    "private-1" = var.private_subnets[0]
    "private-2" = var.private_subnets[1]
  }
}

resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.azure_region
}

resource "azurerm_virtual_network" "vnet" {
  name                = "${var.cluster_name}-vnet"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  address_space = [var.vnet_cidr]
}

resource "azurerm_subnet" "subnets" {
  for_each = local.subnet_map

  name                 = each.key
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name

  address_prefixes = [each.value]
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  dns_prefix         = var.cluster_name
  kubernetes_version = var.kubernetes_version


  default_node_pool {
    name       = "default"
    vm_size    = var.node_vm_size
    vnet_subnet_id = azurerm_subnet.subnets["private-1"].id

    enable_auto_scaling = true
    min_count           = var.node_min_size
    max_count           = var.node_max_size
    node_count          = var.node_desired_size

    zones = var.availability_zones
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"

    outbound_type = "loadBalancer"
  }

  private_cluster_enabled = var.private_cluster_enabled
}
