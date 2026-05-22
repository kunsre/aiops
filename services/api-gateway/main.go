package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strconv"
	"sync/atomic"
	"time"
)

var (
	errorMode  atomic.Bool
	latencyMs  atomic.Int64
	rateLimit  atomic.Int64 // max requests per second, 0 = no limit
	reqCounter atomic.Int64
)

func main() {
	port := getEnv("PORT", "8080")

	mux := http.NewServeMux()

	// Health & metrics
	mux.HandleFunc("/healthz", healthHandler)

	// Proxy routes
	mux.Handle("/api/data-worker/", withMiddleware(proxyHandler("DATA_WORKER_URL", "http://data-worker:8000")))
	mux.Handle("/api/core-business/", withMiddleware(proxyHandler("CORE_BUSINESS_URL", "http://core-business:8081")))
	mux.Handle("/api/bff/", withMiddleware(proxyHandler("BFF_SERVICE_URL", "http://bff-service:3000")))

	// Fault injection
	mux.HandleFunc("/fault/error503", faultError503)
	mux.HandleFunc("/fault/error503/disable", faultError503Disable)
	mux.HandleFunc("/fault/latency/", faultLatency)
	mux.HandleFunc("/fault/ratelimit/", faultRateLimit)
	mux.HandleFunc("/fault/crash", faultCrash)

	log.Printf("api-gateway listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func withMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Error mode
		if errorMode.Load() {
			http.Error(w, `{"error":"service_unavailable","message":"Gateway in error mode"}`, http.StatusServiceUnavailable)
			return
		}

		// Rate limiting
		limit := rateLimit.Load()
		if limit > 0 {
			count := reqCounter.Add(1)
			if count > limit {
				http.Error(w, `{"error":"rate_limit_exceeded","message":"Too many requests"}`, http.StatusTooManyRequests)
				return
			}
		}

		// Latency injection
		if ms := latencyMs.Load(); ms > 0 {
			time.Sleep(time.Duration(ms) * time.Millisecond)
		}

		next.ServeHTTP(w, r)
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if errorMode.Load() {
		w.WriteHeader(http.StatusServiceUnavailable)
		fmt.Fprint(w, `{"status":"error","service":"api-gateway","message":"error mode active"}`)
		return
	}
	fmt.Fprint(w, `{"status":"ok","service":"api-gateway"}`)
}

// === Fault Injection Handlers ===

func faultError503(w http.ResponseWriter, r *http.Request) {
	errorMode.Store(true)
	jsonResp(w, map[string]string{"status": "error_mode_enabled"})
}

func faultError503Disable(w http.ResponseWriter, r *http.Request) {
	errorMode.Store(false)
	jsonResp(w, map[string]string{"status": "error_mode_disabled"})
}

func faultLatency(w http.ResponseWriter, r *http.Request) {
	// Parse /fault/latency/{ms} or /fault/latency/disable
	path := r.URL.Path
	if path == "/fault/latency/disable" {
		latencyMs.Store(0)
		jsonResp(w, map[string]string{"status": "latency_removed"})
		return
	}
	ms, err := strconv.ParseInt(path[len("/fault/latency/"):], 10, 64)
	if err != nil {
		http.Error(w, "invalid ms value", 400)
		return
	}
	latencyMs.Store(ms)
	jsonResp(w, map[string]any{"status": "latency_injected", "latency_ms": ms})
}

func faultRateLimit(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	if path == "/fault/ratelimit/disable" {
		rateLimit.Store(0)
		reqCounter.Store(0)
		jsonResp(w, map[string]string{"status": "ratelimit_disabled"})
		return
	}
	limit, err := strconv.ParseInt(path[len("/fault/ratelimit/"):], 10, 64)
	if err != nil {
		http.Error(w, "invalid limit value", 400)
		return
	}
	rateLimit.Store(limit)
	reqCounter.Store(0)
	jsonResp(w, map[string]any{"status": "ratelimit_enabled", "max_rps": limit})
}

func faultCrash(w http.ResponseWriter, r *http.Request) {
	jsonResp(w, map[string]string{"status": "crashing"})
	go func() {
		time.Sleep(100 * time.Millisecond)
		os.Exit(1)
	}()
}

// === Helpers ===

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

func jsonResp(w http.ResponseWriter, data any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}
