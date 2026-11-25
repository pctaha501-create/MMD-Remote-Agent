//go:build windows

package main

import (
	"fmt"
	"syscall"
	"unsafe"
)

type dataBlob struct { size uint32; data *byte }
var crypt32 = syscall.NewLazyDLL("crypt32.dll")
var kernel32 = syscall.NewLazyDLL("kernel32.dll")
var procProtect = crypt32.NewProc("CryptProtectData")
var procUnprotect = crypt32.NewProc("CryptUnprotectData")
var procLocalFree = kernel32.NewProc("LocalFree")

func protect(input []byte)([]byte,error){
	if len(input)==0{return nil,nil}
	in:=dataBlob{size:uint32(len(input)),data:&input[0]};var out dataBlob
	r,_,e:=procProtect.Call(uintptr(unsafe.Pointer(&in)),0,0,0,0,1,uintptr(unsafe.Pointer(&out)))
	if r==0{return nil,fmt.Errorf("CryptProtectData: %w",e)}
	defer procLocalFree.Call(uintptr(unsafe.Pointer(out.data)))
	return append([]byte(nil),unsafe.Slice(out.data,int(out.size))...),nil
}
func unprotect(input []byte)([]byte,error){
	if len(input)==0{return nil,nil}
	in:=dataBlob{size:uint32(len(input)),data:&input[0]};var out dataBlob
	r,_,e:=procUnprotect.Call(uintptr(unsafe.Pointer(&in)),0,0,0,0,1,uintptr(unsafe.Pointer(&out)))
	if r==0{return nil,fmt.Errorf("CryptUnprotectData: %w",e)}
	defer procLocalFree.Call(uintptr(unsafe.Pointer(out.data)))
	return append([]byte(nil),unsafe.Slice(out.data,int(out.size))...),nil
}