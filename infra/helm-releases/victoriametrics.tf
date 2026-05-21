resource "helm_release" "victoriametrics" {
  name       = "victoriametrics"
  namespace  = "monitoring"
  repository = "https://victoriametrics.github.io/helm-charts"
  chart      = "victoria-metrics-single"
  version    = "0.14.6"

  set {
    name  = "server.scrape.enabled"
    value = "true"
  }

  set {
    name  = "server.resources.requests.memory"
    value = "256Mi"
  }

  set {
    name  = "server.resources.limits.memory"
    value = "512Mi"
  }

  depends_on = [kubernetes_namespace.monitoring]
}
