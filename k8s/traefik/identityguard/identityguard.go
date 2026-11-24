// Copyright (c) Hewlett Packard Enterprise, 2026. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package identityguard

import (
	"context"
	"net/http"
)

type Config struct{}

func CreateConfig() *Config {
	return &Config{}
}

type guard struct {
	next http.Handler
}

func New(_ context.Context, next http.Handler, _ *Config, _ string) (http.Handler, error) {
	return &guard{next: next}, nil
}

func (g *guard) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Header.Get("X-Forwarded-User") == "" || r.Header.Get("X-Forwarded-Groups") == "" {
		http.Error(w, "authentication service did not provide an identity", http.StatusServiceUnavailable)
		return
	}
	g.next.ServeHTTP(w, r)
}
