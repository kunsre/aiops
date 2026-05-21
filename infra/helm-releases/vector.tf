resource "helm_release" "vector" {
  name       = "vector"
  namespace  = "monitoring"
  repository = "https://helm.vector.dev"
  chart      = "vector"
  version    = "0.37.0"

  set {
    name  = "role"
    value = "Agent"
  }

  set {
    name  = "resources.requests.memory"
    value = "64Mi"
  }

  set {
    name  = "resources.limits.memory"
    value = "128Mi"
  }

  depends_on = [kubernetes_namespace.monitoring]
}
