package main

import "time"

// BUG: 프록시 타임아웃 1초 → bff-service 응답 시간 초과 시 502
// 정상값: 30 * time.Second
var ProxyTimeout = 1 * time.Second

// BUG: 유휴 연결 1개 → 동시 요청 시 성능 저하
// 정상값: 100
var MaxIdleConns = 1

// BUG: 헤더 읽기 100ms → 느린 클라이언트 차단
// 정상값: 10 * time.Second
var ReadHeaderTimeout = 100 * time.Millisecond
