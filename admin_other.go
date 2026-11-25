//go:build !windows

package main

import "context"
import "os/exec"

func isAdmin() bool { return false }
func syscallCommand(ctx context.Context, command string) *exec.Cmd { return exec.CommandContext(ctx,"sh","-lc",command) }
func protect(b []byte)([]byte,error){return b,nil}
func unprotect(b []byte)([]byte,error){return b,nil}
