//go:build windows

package main

import (
	"syscall"
	"unsafe"
)

var (
	shell32 = syscall.NewLazyDLL("shell32.dll")
	procIsUserAnAdmin = shell32.NewProc("IsUserAnAdmin")
)
func isAdmin() bool {
	r,_,_:=procIsUserAnAdmin.Call()
	_ = unsafe.Pointer(nil)
	return r!=0
}
