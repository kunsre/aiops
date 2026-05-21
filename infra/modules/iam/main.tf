resource "aws_iam_policy" "bedrock_invoke" {
  name        = "${var.prefix}-bedrock-invoke"
  description = "Allow Bedrock model invocation for AIOps agents"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = "arn:aws:bedrock:${var.region}::foundation-model/*"
      }
    ]
  })

  tags = var.tags
}

module "irsa_agent" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "5.48.0"

  role_name = "${var.prefix}-agent-irsa"

  oidc_providers = {
    main = {
      provider_arn               = var.oidc_provider_arn
      namespace_service_accounts = ["aiops:aiops-agent"]
    }
  }

  role_policy_arns = {
    bedrock = aws_iam_policy.bedrock_invoke.arn
  }

  tags = var.tags
}
