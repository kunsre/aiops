package com.aiops.core;

import org.springframework.web.bind.annotation.*;

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
    public List<Item> findAll() {
        return repository.findAll();
    }

    @GetMapping("/{id}")
    public Item findById(@PathVariable Long id) {
        return repository.findById(id).orElseThrow();
    }

    @PostMapping
    public Item create(@RequestBody Item item) {
        return repository.save(item);
    }

    @DeleteMapping("/{id}")
    public Map<String, String> delete(@PathVariable Long id) {
        repository.deleteById(id);
        return Map.of("status", "deleted");
    }
}
