resource "helm_release" "victorialogs" {
  name       = "victorialogs"
  namespace  = "monitoring"
  repository = "https://victoriametrics.github.io/helm-charts"
  chart      = "victoria-logs-single"
  version    = "0.8.14"

  set {
    name  = "server.resources.requests.memory"
    value = "128Mi"
  }

  set {
    name  = "server.resources.limits.memory"
    value = "256Mi"
  }

  depends_on = [kubernetes_namespace.monitoring]
}
