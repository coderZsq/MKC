package middleware

import (
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// requestRecord tracks the number of requests and window start for a single client.
type requestRecord struct {
	count  int
	window time.Time
}

// RateLimiter limits requests per IP per endpoint using an in-memory sliding window.
type RateLimiter struct {
	requests      int
	window        time.Duration
	mu            sync.Mutex
	recordsByPath map[string]*requestRecord
}

// NewRateLimiter creates an in-memory rate limiter.
func NewRateLimiter(requests int, windowSeconds int) *RateLimiter {
	return &RateLimiter{
		requests:      requests,
		window:        time.Duration(windowSeconds) * time.Second,
		recordsByPath: make(map[string]*requestRecord),
	}
}

// Limit returns a middleware that enforces the rate limit.
func (rl *RateLimiter) Limit() gin.HandlerFunc {
	return func(c *gin.Context) {
		key := rl.key(c)
		now := time.Now()

		rl.mu.Lock()
		defer rl.mu.Unlock()

		rec, exists := rl.recordsByPath[key]
		if !exists || now.After(rec.window.Add(rl.window)) {
			rl.recordsByPath[key] = &requestRecord{count: 1, window: now}
			c.Next()
			return
		}

		rec.count++
		if rec.count > rl.requests {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"success": false,
				"data":    nil,
				"error": gin.H{
					"code":    "TOO_MANY_REQUESTS",
					"message": "rate limit exceeded",
				},
				"meta": nil,
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

func (rl *RateLimiter) key(c *gin.Context) string {
	ip, _, err := net.SplitHostPort(c.Request.RemoteAddr)
	if err != nil {
		ip = c.Request.RemoteAddr
	}
	return ip + "|" + c.Request.URL.Path
}
