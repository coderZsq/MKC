package storage

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
)

// ObjectStorage abstracts file storage (MinIO/S3).
type ObjectStorage interface {
	PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error
	RemoveObject(ctx context.Context, key string) error
	PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error)
}

// MinIOClient implements ObjectStorage using minio-go/v7.
type MinIOClient struct {
	client *minio.Client
	bucket string
}

// NewMinIOClient creates a MinIO storage client and ensures the bucket exists.
func NewMinIOClient(cfg config.MinIOConfig) (*MinIOClient, error) {
	client, err := minio.New(cfg.Endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
		Secure: cfg.UseSSL,
		Region: cfg.Region,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create minio client: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	exists, err := client.BucketExists(ctx, cfg.Bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to check bucket existence: %w", err)
	}
	if !exists {
		if err := client.MakeBucket(ctx, cfg.Bucket, minio.MakeBucketOptions{Region: cfg.Region}); err != nil {
			return nil, fmt.Errorf("failed to make bucket: %w", err)
		}
	}

	return &MinIOClient{client: client, bucket: cfg.Bucket}, nil
}

// PutObject uploads an object to MinIO.
func (m *MinIOClient) PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
	_, err := m.client.PutObject(ctx, m.bucket, key, reader, size, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return fmt.Errorf("failed to put object: %w", err)
	}
	return nil
}

// RemoveObject deletes an object from MinIO.
func (m *MinIOClient) RemoveObject(ctx context.Context, key string) error {
	if err := m.client.RemoveObject(ctx, m.bucket, key, minio.RemoveObjectOptions{}); err != nil {
		return fmt.Errorf("failed to remove object: %w", err)
	}
	return nil
}

// PresignedGetURL generates a temporary GET URL for an object.
func (m *MinIOClient) PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	url, err := m.client.PresignedGetObject(ctx, m.bucket, key, expiry, nil)
	if err != nil {
		return "", fmt.Errorf("failed to generate presigned url: %w", err)
	}
	return url.String(), nil
}

var _ ObjectStorage = (*MinIOClient)(nil)
