//go:build windows

package main

import "syscall"

var (
	shell32 = syscall.NewLazyDLL("shell32.dll")
	procIsUserAnAdmin = shell32.NewProc("IsUserAnAdmin")
)

func isAdmin() bool {
	r, _, _ := procIsUserAnAdmin.Call()
	return r != 0
}
