package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
)

func main() {
	http.HandleFunc("/users", func(w http.ResponseWriter, r *http.Request) {
		id := r.URL.Query().Get("id")
		db, _ := sql.Open("postgres", "user=postgres dbname=test sslmode=disable")

		// SQL Injection Vulnerability
		// Semgrep rule: go.lang.security.audit.database.sql-injection
		query := fmt.Sprintf("SELECT * FROM users WHERE id = %s", id)
		rows, err := db.Query(query)
		if err != nil {
			log.Fatal(err)
		}
		defer rows.Close()
	})

    // Hardcoded API Key
    apiKey := "AKIAIOSFODNN7EXAMPLE"
    fmt.Println(apiKey)
}
