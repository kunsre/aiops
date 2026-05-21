variable "prefix" {
  type    = string
  default = "aiops"
}

variable "repository_names" {
  type = list(string)
  default = [
    "api-gateway",
    "data-worker",
    "core-business",
    "bff-service",
  ]
}

variable "tags" {
  type    = map(string)
  default = {}
}
