variable "prefix" {
  type    = string
  default = "aiops"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "oidc_provider_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
