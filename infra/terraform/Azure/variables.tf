variable "azure_region" {
  type    = string
  default = "germanywestcentral"
}

variable "resource_group_name" {
  type    = string
  default = null
}

variable "cluster_name" {
  type    = string
  default = "lichtcase-aks"
}

variable "kubernetes_version" {
  type    = string
  default = null
}

variable "vnet_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnets" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  type    = list(string)
  default = ["10.0.3.0/24", "10.0.4.0/24"]
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_vm_size" {
  type    = string
  default = "Standard_D4s_v5"
  # Roughly similar “feel” to t3.large (general-purpose).
}

variable "availability_zones" {
  type    = list(string)
  default = ["1", "2"]
}

variable "private_cluster_enabled" {
  type    = bool
  default = false
}
