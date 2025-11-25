package main

import (
	"github.com/gin-gonic/gin"
	"net/http"
)

func main() {
	r := gin.Default()
	
	// Low severity: Information disclosure via debug endpoint
	r.GET("/debug/config", func(c *gin.Context) {
		config := map[string]string{
			"db_host": "db-service:5432",
			"version": "1.0.0",
			"env":     "production",
		}
		c.JSON(http.StatusOK, config)
	})
	
	r.GET("/api/data", func(c *gin.Context) {
		// Proxy to internal db-service
		c.JSON(http.StatusOK, gin.H{"message": "proxied"})
	})
	
	r.Run(":8080")
}
