terraform {
  backend "s3" {
    bucket  = "aiops-terraform-state"
    key     = "dev/terraform.tfstate"
    region  = "ap-northeast-2"
    encrypt = true
  }
}
