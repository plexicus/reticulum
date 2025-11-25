package com.example.edge;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

@SpringBootApplication
@RestController
public class EdgeService {
    
    private static final Logger logger = LogManager.getLogger(EdgeService.class);
    
    // LOW SEVERITY: Information disclosure via error messages
    @GetMapping("/api/status")
    public String getStatus() {
        return "Service: edge-service, Version: 1.0.0, Environment: production";
    }
    
    // LOW SEVERITY: Verbose logging (potential info disclosure)
    @PostMapping("/api/log")
    public String logMessage(@RequestBody String message) {
        logger.info("User message: {}", message);
        return "Logged";
    }
    
    public static void main(String[] args) {
        SpringApplication.run(EdgeService.class, args);
    }
}
