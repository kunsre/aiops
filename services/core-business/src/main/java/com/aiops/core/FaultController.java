package com.aiops.core;

import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

@RestController
@RequestMapping("/fault")
public class FaultController {

    private static final AtomicBoolean errorMode = new AtomicBoolean(false);
    private static final AtomicInteger latencyMs = new AtomicInteger(0);
    private static final AtomicBoolean deadlock = new AtomicBoolean(false);

    public static boolean isErrorMode() { return errorMode.get(); }
    public static int getLatencyMs() { return latencyMs.get(); }
    public static boolean isDeadlocked() { return deadlock.get(); }

    @PostMapping("/error500")
    public Map<String, String> enableError() {
        errorMode.set(true);
        return Map.of("status", "error_mode_enabled", "message", "All DB operations will throw SQLException");
    }

    @PostMapping("/error500/disable")
    public Map<String, String> disableError() {
        errorMode.set(false);
        return Map.of("status", "error_mode_disabled");
    }

    @PostMapping("/latency/{ms}")
    public Map<String, Object> setLatency(@PathVariable int ms) {
        latencyMs.set(ms);
        return Map.of("status", "latency_injected", "latency_ms", ms);
    }

    @PostMapping("/latency/disable")
    public Map<String, String> disableLatency() {
        latencyMs.set(0);
        return Map.of("status", "latency_removed");
    }

    @PostMapping("/deadlock")
    public Map<String, String> enableDeadlock() {
        deadlock.set(true);
        // Simulate a thread deadlock by holding locks
        new Thread(() -> {
            synchronized (FaultController.class) {
                try { Thread.sleep(Long.MAX_VALUE); } catch (InterruptedException ignored) {}
            }
        }).start();
        return Map.of("status", "deadlock_simulated", "message", "Thread pool will be exhausted");
    }

    @PostMapping("/connection-leak")
    public Map<String, String> connectionLeak() {
        // Simulate DB connection pool exhaustion
        errorMode.set(true);
        return Map.of("status", "connection_leak_enabled", "message", "Simulating HikariCP pool exhaustion");
    }

    @PostMapping("/crash")
    public Map<String, String> crash() {
        new Thread(() -> {
            try { Thread.sleep(100); } catch (InterruptedException ignored) {}
            System.exit(1);
        }).start();
        return Map.of("status", "crashing");
    }
}
