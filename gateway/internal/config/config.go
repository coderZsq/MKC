package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// AppConfig holds application identity and runtime environment.
type AppConfig struct {
	Name    string `mapstructure:"name"`
	Version string `mapstructure:"version"`
	Env     string `mapstructure:"env"`
}

// ServerConfig holds HTTP server settings.
type ServerConfig struct {
	Port int    `mapstructure:"port"`
	Mode string `mapstructure:"mode"`
}

// LogConfig holds logging options.
type LogConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"`
}

// MySQLConfig holds database connection options.
type MySQLConfig struct {
	Host            string        `mapstructure:"host"`
	Port            int           `mapstructure:"port"`
	User            string        `mapstructure:"user"`
	Password        string        `mapstructure:"password"`
	DBName          string        `mapstructure:"dbname"`
	MaxOpenConns    int           `mapstructure:"max_open_conns"`
	MaxIdleConns    int           `mapstructure:"max_idle_conns"`
	ConnMaxLifetime time.Duration `mapstructure:"conn_max_lifetime"`
}

// RedisConfig holds Redis connection options.
type RedisConfig struct {
	Addr     string `mapstructure:"addr"`
	Password string `mapstructure:"password"`
	DB       int    `mapstructure:"db"`
	PoolSize int    `mapstructure:"pool_size"`
}

// JWTConfig holds token signing options.
type JWTConfig struct {
	Secret     string        `mapstructure:"secret"`
	AccessTTL  time.Duration `mapstructure:"access_ttl"`
	RefreshTTL time.Duration `mapstructure:"refresh_ttl"`
}

// AIServiceConfig holds AI service client options.
type AIServiceConfig struct {
	BaseURL     string        `mapstructure:"base_url"`
	Timeout     time.Duration `mapstructure:"timeout"`
	InternalKey string        `mapstructure:"internal_key"`
}

// TaskConfig holds asynchronous task dispatch and retry options.
type TaskConfig struct {
	MaxRetries      int             `mapstructure:"max_retries"`
	RetryDelays     []time.Duration `mapstructure:"retry_delays"`
	RetryCooldown   time.Duration   `mapstructure:"retry_cooldown"`
	DispatchTimeout time.Duration   `mapstructure:"dispatch_timeout"`
	AutoSummary     bool            `mapstructure:"auto_summary"`
}

// QAConfig holds Q&A SSE options.
type QAConfig struct {
	Timeout           time.Duration `mapstructure:"timeout"`
	MaxSSEConnections int           `mapstructure:"max_sse_connections"`
}

// ResilienceConfig holds timeout and retry policy defaults for external dependencies.
type ResilienceConfig struct {
	UploadTimeout    time.Duration `mapstructure:"upload_timeout"`
	RetrievalTimeout time.Duration `mapstructure:"retrieval_timeout"`
	LLMTimeout       time.Duration `mapstructure:"llm_timeout"`
	MaxRetries       int           `mapstructure:"max_retries"`
	RetryBackoff     time.Duration `mapstructure:"retry_backoff"`
}

// ObservabilityConfig holds tracing and telemetry options.
type ObservabilityConfig struct {
	Tracing TracingConfig `mapstructure:"tracing"`
	Metrics MetricsConfig `mapstructure:"metrics"`
}

// TracingConfig holds OpenTelemetry tracing options.
type TracingConfig struct {
	Enabled     bool    `mapstructure:"enabled"`
	ServiceName string  `mapstructure:"service_name"`
	Exporter    string  `mapstructure:"exporter"`
	Endpoint    string  `mapstructure:"endpoint"`
	SampleRatio float64 `mapstructure:"sample_ratio"`
}

// MetricsConfig holds Prometheus metrics options.
type MetricsConfig struct {
	Enabled   bool   `mapstructure:"enabled"`
	Path      string `mapstructure:"path"`
	Namespace string `mapstructure:"namespace"`
}

// ConversationConfig holds conversation and context-window options.
type ConversationConfig struct {
	DefaultTitle       string `mapstructure:"default_title"`
	MaxContextMessages int    `mapstructure:"max_context_messages"`
	MaxContextTokens   int    `mapstructure:"max_context_tokens"`
}

// MinIOConfig holds object storage connection options.
type MinIOConfig struct {
	Endpoint        string        `mapstructure:"endpoint"`
	AccessKey       string        `mapstructure:"access_key"`
	SecretKey       string        `mapstructure:"secret_key"`
	Bucket          string        `mapstructure:"bucket"`
	ResultsBucket   string        `mapstructure:"results_bucket"`
	PresignedExpiry time.Duration `mapstructure:"presigned_expiry"`
	UseSSL          bool          `mapstructure:"use_ssl"`
	Region          string        `mapstructure:"region"`
}

// Config is the top-level configuration container.
type Config struct {
	App           AppConfig           `mapstructure:"app"`
	Server        ServerConfig        `mapstructure:"server"`
	Log           LogConfig           `mapstructure:"log"`
	MySQL         MySQLConfig         `mapstructure:"mysql"`
	Redis         RedisConfig         `mapstructure:"redis"`
	JWT           JWTConfig           `mapstructure:"jwt"`
	AIService     AIServiceConfig     `mapstructure:"ai_service"`
	Task          TaskConfig          `mapstructure:"task"`
	QA            QAConfig            `mapstructure:"qa"`
	Resilience    ResilienceConfig    `mapstructure:"resilience"`
	Observability ObservabilityConfig `mapstructure:"observability"`
	Conversation  ConversationConfig  `mapstructure:"conversation"`
	MinIO         MinIOConfig         `mapstructure:"minio"`
}

// Load reads configuration from the given YAML file and environment variables.
// Environment variables use the APP_ prefix and underscores for nesting, e.g.
// APP_SERVER_PORT overrides server.port.
func Load(path string) (*Config, error) {
	viper.SetConfigFile(path)
	viper.SetEnvPrefix("APP")
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config: %w", err)
	}

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	if err := cfg.validate(); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func (c *Config) validate() error {
	if c.Server.Port <= 0 {
		return fmt.Errorf("server.port must be a positive integer")
	}
	if c.App.Env == "" {
		c.App.Env = "dev"
	}
	if c.Server.Mode == "" {
		c.Server.Mode = "debug"
	}
	if c.Log.Level == "" {
		c.Log.Level = "info"
	}
	if c.Log.Format == "" {
		c.Log.Format = "json"
	}
	if c.JWT.Secret == "" {
		return fmt.Errorf("jwt.secret must be set")
	}
	if c.JWT.AccessTTL <= 0 {
		c.JWT.AccessTTL = 15 * time.Minute
	}
	if c.JWT.RefreshTTL <= 0 {
		c.JWT.RefreshTTL = 7 * 24 * time.Hour
	}
	if c.AIService.BaseURL == "" {
		return fmt.Errorf("ai_service.base_url must be set")
	}
	if c.AIService.InternalKey == "" {
		return fmt.Errorf("ai_service.internal_key must be set")
	}
	if c.AIService.Timeout <= 0 {
		c.AIService.Timeout = 60 * time.Second
	}
	if c.Task.MaxRetries <= 0 {
		c.Task.MaxRetries = 3
	}
	if len(c.Task.RetryDelays) == 0 {
		c.Task.RetryDelays = []time.Duration{60 * time.Second, 5 * time.Minute, 15 * time.Minute}
	}
	if c.Task.RetryCooldown <= 0 {
		c.Task.RetryCooldown = 5 * time.Minute
	}
	if c.Task.DispatchTimeout <= 0 {
		c.Task.DispatchTimeout = 10 * time.Second
	}
	if c.QA.Timeout <= 0 {
		c.QA.Timeout = 120 * time.Second
	}
	if c.QA.MaxSSEConnections <= 0 {
		c.QA.MaxSSEConnections = 10
	}
	if c.Resilience.UploadTimeout <= 0 {
		c.Resilience.UploadTimeout = 60 * time.Second
	}
	if c.Resilience.RetrievalTimeout <= 0 {
		c.Resilience.RetrievalTimeout = 20 * time.Second
	}
	if c.Resilience.LLMTimeout <= 0 {
		c.Resilience.LLMTimeout = 60 * time.Second
	}
	if c.Resilience.MaxRetries < 0 {
		c.Resilience.MaxRetries = 0
	}
	if c.Resilience.RetryBackoff <= 0 {
		c.Resilience.RetryBackoff = 300 * time.Millisecond
	}
	if c.Observability.Tracing.ServiceName == "" {
		c.Observability.Tracing.ServiceName = c.App.Name
	}
	if c.Observability.Tracing.Exporter == "" {
		c.Observability.Tracing.Exporter = "noop"
	}
	if c.Observability.Tracing.SampleRatio <= 0 || c.Observability.Tracing.SampleRatio > 1 {
		c.Observability.Tracing.SampleRatio = 0.1
	}
	if c.Observability.Metrics.Path == "" {
		c.Observability.Metrics.Path = "/metrics"
	}
	if c.Observability.Metrics.Namespace == "" {
		c.Observability.Metrics.Namespace = "mkc"
	}
	if c.Conversation.DefaultTitle == "" {
		c.Conversation.DefaultTitle = "新会话"
	}
	if c.Conversation.MaxContextMessages <= 0 {
		c.Conversation.MaxContextMessages = 20
	}
	if c.Conversation.MaxContextTokens <= 0 {
		c.Conversation.MaxContextTokens = 4096
	}
	if c.MinIO.PresignedExpiry <= 0 {
		c.MinIO.PresignedExpiry = time.Hour
	}
	if c.MinIO.ResultsBucket == "" {
		c.MinIO.ResultsBucket = c.MinIO.Bucket
	}
	return nil
}
