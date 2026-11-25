//go:build windows

package main

import (
 "context"
 "os/exec"
)

func isAdmin() bool { return exec.Command("net","session").Run()==nil }
func syscallCommand(ctx context.Context, command string) *exec.Cmd {
 return exec.CommandContext(ctx,"powershell.exe","-NoLogo","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-Command",command)
}
