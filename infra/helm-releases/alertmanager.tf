resource "helm_release" "alertmanager" {
  name       = "alertmanager"
  namespace  = "monitoring"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "alertmanager"
  version    = "1.14.0"

  values = [
    yamlencode({
      config = {
        global = {
          resolve_timeout = "1m"
        }
        route = {
          receiver   = "aiops-webhook"
          group_by   = ["alertname", "namespace", "service"]
          group_wait = "10s"
        }
        receivers = [{
          name = "aiops-webhook"
          webhook_configs = [{
            url            = "http://aiops-agent.aiops.svc.cluster.local:9090/webhook/alertmanager"
            send_resolved  = true
          }]
        }]
      }
    })
  ]

  depends_on = [kubernetes_namespace.monitoring]
}
