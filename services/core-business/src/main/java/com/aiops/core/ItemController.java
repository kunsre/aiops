package com.aiops.core;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/items")
public class ItemController {

    private final ItemRepository repository;

    public ItemController(ItemRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public List<Item> findAll() throws InterruptedException {
        applyFaults();
        return repository.findAll();
    }

    @GetMapping("/{id}")
    public Item findById(@PathVariable Long id) throws InterruptedException {
        applyFaults();
        return repository.findById(id).orElseThrow();
    }

    @PostMapping
    public Item create(@RequestBody Item item) throws InterruptedException {
        applyFaults();
        return repository.save(item);
    }

    @DeleteMapping("/{id}")
    public Map<String, String> delete(@PathVariable Long id) throws InterruptedException {
        applyFaults();
        repository.deleteById(id);
        return Map.of("status", "deleted");
    }

    private void applyFaults() throws InterruptedException {
        if (FaultController.isErrorMode()) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                "java.sql.SQLException: HikariPool-1 - Connection is not available, request timed out after 30000ms");
        }
        int latency = FaultController.getLatencyMs();
        if (latency > 0) {
            Thread.sleep(latency);
        }
    }
}
