//go:build windows

package main

import (
	"context"
	"os/exec"
	"syscall"
)

var shell32 = syscall.NewLazyDLL("shell32.dll")
var isUserAdminProc = shell32.NewProc("IsUserAnAdmin")

func isAdmin() bool {
	r, _, _ := isUserAdminProc.Call()
	return r != 0
}

func syscallCommand(ctx context.Context, command string) *exec.Cmd {
	return exec.CommandContext(ctx, "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command)
}
