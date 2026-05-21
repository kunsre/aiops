package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
)

func main() {
	port := getEnv("PORT", "8080")

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", healthHandler)
	mux.Handle("/api/data-worker/", proxyHandler("DATA_WORKER_URL", "http://data-worker:8000"))
	mux.Handle("/api/core-business/", proxyHandler("CORE_BUSINESS_URL", "http://core-business:8081"))
	mux.Handle("/api/bff/", proxyHandler("BFF_SERVICE_URL", "http://bff-service:3000"))

	log.Printf("api-gateway listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprint(w, `{"status":"ok","service":"api-gateway"}`)
}

func proxyHandler(envKey, defaultURL string) http.Handler {
	target := getEnv(envKey, defaultURL)
	u, err := url.Parse(target)
	if err != nil {
		log.Fatalf("invalid proxy target %s: %v", target, err)
	}
	return httputil.NewSingleHostReverseProxy(u)
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
