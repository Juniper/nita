// Copyright (c) Hewlett Packard Enterprise, 2026. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package bodylimit

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
)

type Config struct {
	MaxBytes int64 `json:"maxBytes,omitempty"`
}

func CreateConfig() *Config {
	return &Config{MaxBytes: 20 * 1024 * 1024}
}

type limiter struct {
	next     http.Handler
	maxBytes int64
}

func New(_ context.Context, next http.Handler, config *Config, _ string) (http.Handler, error) {
	if config.MaxBytes <= 0 {
		return nil, fmt.Errorf("maxBytes must be positive")
	}
	return &limiter{next: next, maxBytes: config.MaxBytes}, nil
}

func (l *limiter) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.ContentLength > l.maxBytes {
		http.Error(w, "request body too large", http.StatusRequestEntityTooLarge)
		return
	}
	if r.Body == nil || r.Body == http.NoBody {
		l.next.ServeHTTP(w, r)
		return
	}

	body, err := os.CreateTemp("", "nita-proxy-body-*")
	if err != nil {
		log.Printf("body limit: creating temporary file: %v", err)
		http.Error(w, "unable to process request body", http.StatusInternalServerError)
		return
	}
	defer func() {
		if err := body.Close(); err != nil {
			log.Printf("body limit: closing temporary file: %v", err)
		}
		if err := os.Remove(body.Name()); err != nil {
			log.Printf("body limit: removing temporary file: %v", err)
		}
	}()

	size, err := io.Copy(body, io.LimitReader(r.Body, l.maxBytes+1))
	if err != nil {
		log.Printf("body limit: reading request body: %v", err)
		http.Error(w, "unable to read request body", http.StatusBadRequest)
		return
	}
	if size > l.maxBytes {
		http.Error(w, "request body too large", http.StatusRequestEntityTooLarge)
		return
	}
	if _, err := body.Seek(0, io.SeekStart); err != nil {
		log.Printf("body limit: rewinding temporary file: %v", err)
		http.Error(w, "unable to process request body", http.StatusInternalServerError)
		return
	}

	r.Body = io.NopCloser(body)
	r.ContentLength = size
	r.TransferEncoding = nil
	l.next.ServeHTTP(w, r)
}
