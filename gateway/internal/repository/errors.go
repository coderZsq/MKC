package repository

import "errors"

// ErrNotFound indicates that the requested entity does not exist.
var ErrNotFound = errors.New("NOT_FOUND")
