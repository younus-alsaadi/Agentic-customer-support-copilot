output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "cluster_fqdn" {
  value = azurerm_kubernetes_cluster.aks.fqdn
}

output "cluster_host" {
  value = azurerm_kubernetes_cluster.aks.kube_config[0].host
}

output "cluster_ca_certificate" {
  value = azurerm_kubernetes_cluster.aks.kube_config[0].cluster_ca_certificate
}

output "vnet_id" {
  value = azurerm_virtual_network.vnet.id
}

output "public_subnet_ids" {
  value = [
    azurerm_subnet.subnets["public-1"].id,
    azurerm_subnet.subnets["public-2"].id
  ]
}

output "private_subnet_ids" {
  value = [
    azurerm_subnet.subnets["private-1"].id,
    azurerm_subnet.subnets["private-2"].id
  ]
}
