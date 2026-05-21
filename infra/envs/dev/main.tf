terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  name = "aiops-${var.environment}"
  azs  = slice(data.aws_availability_zones.available.names, 0, 3)

  tags = {
    Project     = "aiops"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source = "../../modules/vpc"

  name            = local.name
  cidr            = var.vpc_cidr
  azs             = local.azs
  private_subnets = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 4)]
  tags            = local.tags
}

module "ecr" {
  source = "../../modules/ecr"

  prefix = local.name
  tags   = local.tags
}

module "iam" {
  source = "../../modules/iam"

  prefix            = local.name
  region            = var.region
  oidc_provider_arn = module.eks.oidc_provider_arn
  tags              = local.tags
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.name
  cluster_version    = var.eks_version
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  bedrock_policy_arn = module.iam.bedrock_policy_arn
  tags               = local.tags
}
