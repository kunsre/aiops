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

	// 단일 진입점: 모든 API 요청은 bff-service로 프록시
	// BUG: ProxyTimeout=1s → bff 응답이 1초 넘으면 502
	bffURL := getEnv("BFF_SERVICE_URL", "http://bff-service:3000")
	mux.Handle("/api/", makeProxy(bffURL, "/api"))

	log.Printf("api-gateway listening on :%s", port)
	server := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: ReadHeaderTimeout,
	}
	if err := server.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprint(w, `{"status":"ok","service":"api-gateway"}`)
}

func makeProxy(targetURL string, stripPrefix string) http.Handler {
	u, err := url.Parse(targetURL)
	if err != nil {
		log.Fatalf("invalid proxy target %s: %v", targetURL, err)
	}
	proxy := httputil.NewSingleHostReverseProxy(u)
	proxy.Transport = &http.Transport{
		ResponseHeaderTimeout: ProxyTimeout,
		MaxIdleConns:          MaxIdleConns,
	}
	return http.StripPrefix(stripPrefix, proxy)
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

