package repository

import "errors"

// ErrNotFound indicates that the requested entity does not exist.
var ErrNotFound = errors.New("NOT_FOUND")

// ErrForbidden indicates that the requested entity exists but is owned by another principal.
var ErrForbidden = errors.New("FORBIDDEN")
