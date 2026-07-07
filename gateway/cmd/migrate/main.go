package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func main() {
	if len(os.Args) < 2 {
		usage()
	}

	dsn := os.Getenv("MYSQL_DSN")
	if dsn == "" {
		fmt.Println("MYSQL_DSN environment variable is required")
		os.Exit(1)
	}

	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		fmt.Printf("failed to connect to database: %v\n", err)
		os.Exit(1)
	}

	switch strings.ToLower(os.Args[1]) {
	case "up":
		if err := repository.AutoMigrate(db); err != nil {
			fmt.Printf("migration up failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("migration up completed")
	case "down":
		if err := repository.DropAll(db); err != nil {
			fmt.Printf("migration down failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("migration down completed")
	default:
		usage()
	}
}

func usage() {
	fmt.Println("usage: go run ./cmd/migrate [up|down]")
	os.Exit(1)
}
