output "bedrock_policy_arn" {
  value = aws_iam_policy.bedrock_invoke.arn
}

output "agent_role_arn" {
  value = module.irsa_agent.iam_role_arn
}
