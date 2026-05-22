package main

import "time"

// BUG SCENARIOS (Generator가 패치할 대상):
//
// ProxyTimeout: 1초로 설정 → upstream 응답이 1초 넘으면 전부 timeout (정상: 30초)
// MaxIdleConns: 1로 설정 → connection reuse 불가, 성능 저하 (정상: 100)
// ReadHeaderTimeout: 100ms → 느린 클라이언트 요청 거부 (정상: 10초)

// BUG: 프록시 타임아웃 1초 → 대부분의 upstream 응답 timeout
var ProxyTimeout = 1 * time.Second

// BUG: 유휴 연결 1개 → 동시 요청 시 매번 새 연결 생성
var MaxIdleConns = 1

// BUG: 헤더 읽기 100ms → 느린 네트워크 클라이언트 차단
var ReadHeaderTimeout = 100 * time.Millisecond
