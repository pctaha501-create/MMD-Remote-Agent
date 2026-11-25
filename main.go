//go:build windows

package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

const gateway = "https://ssh.the-end.shop"

type job struct { ID string `json:"id"`; Command string `json:"command"` }
type pollResponse struct { Job *job `json:"job"` }
type resultPayload struct { ID string `json:"id"`; Output string `json:"output"`; ExitCode int `json:"exit_code"` }

type agent struct { token string; client *http.Client }

func newAgent(token string) *agent {
	return &agent{token: token, client: &http.Client{Timeout: 35*time.Second, Transport: &http.Transport{Proxy: http.ProxyFromEnvironment, MaxIdleConns: 2, IdleConnTimeout: 20*time.Second, TLSHandshakeTimeout: 10*time.Second}}}
}
func (a *agent) request(ctx context.Context, path string, body any, out any) error {
	var rd io.Reader
	if body != nil { b,err:=json.Marshal(body); if err!=nil{return err}; rd=bytes.NewReader(b) }
	req,err:=http.NewRequestWithContext(ctx,http.MethodPost,gateway+path,rd); if err!=nil{return err}
	req.Header.Set("Authorization","Bearer "+a.token); req.Header.Set("Accept","application/json")
	if body!=nil { req.Header.Set("Content-Type","application/json") }
	resp,err:=a.client.Do(req); if err!=nil{return err}; defer resp.Body.Close()
	if resp.StatusCode<200||resp.StatusCode>=300 { b,_:=io.ReadAll(io.LimitReader(resp.Body,2048)); return fmt.Errorf("gateway returned HTTP %d: %s",resp.StatusCode,strings.TrimSpace(string(b))) }
	if out!=nil { return json.NewDecoder(io.LimitReader(resp.Body,1<<20)).Decode(out) }
	_,err=io.Copy(io.Discard,resp.Body); return err
}
func (a *agent) runCommand(command string) (string,int) {
	ctx,cancel:=context.WithTimeout(context.Background(),30*time.Minute); defer cancel()
	cmd:=exec.CommandContext(ctx,"powershell.exe","-NoLogo","-NoProfile","-NonInteractive","-Command",command)
	var out bytes.Buffer; cmd.Stdout=&out; cmd.Stderr=&out
	err:=cmd.Run()
	if ctx.Err()!=nil { return out.String()+"\nCommand timed out or was cancelled.",124 }
	if err==nil{return out.String(),0}
	var ee *exec.ExitError; if errors.As(err,&ee){return out.String(),ee.ExitCode()}
	return out.String()+"\n"+err.Error(),1
}
func confirm(j job) bool {
	fmt.Println("\n============================================================")
	fmt.Println("درخواست اجرای دستور جدید (با دسترسی Administrator)")
	fmt.Println("Job:",j.ID)
	fmt.Println("------------------------------------------------------------")
	fmt.Println(j.Command)
	fmt.Println("------------------------------------------------------------")
	fmt.Print("برای اجرا دقیقاً YES را وارد کن؛ هر چیز دیگری = رد: ")
	line,_:=bufio.NewReader(os.Stdin).ReadString('\n')
	return strings.EqualFold(strings.TrimSpace(line),"YES")
}
func main() {
	fmt.Println("MMD Remote Agent | Windows")
	if !isAdmin() { fmt.Fprintln(os.Stderr,"ERROR: برنامه باید با دسترسی Administrator اجرا شود."); os.Exit(1) }
	token:=strings.TrimSpace(os.Getenv("SSH_GATEWAY_TOKEN"))
	if token=="" { fmt.Fprintln(os.Stderr,"SSH_GATEWAY_TOKEN is not set. Set the agent token in the environment, then reopen this app."); os.Exit(2) }
	a:=newAgent(token)
	ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM); defer stop()
	fmt.Println("Administrator: OK")
	fmt.Println("Gateway:",gateway)
	fmt.Println("Connecting... (Ctrl+C to exit)")
	backoff:=2*time.Second
	for {
		if ctx.Err()!=nil { fmt.Println("\nDisconnected."); return }
		var p pollResponse
		err:=a.request(ctx,"/agent/poll",nil,&p)
		if err!=nil {
			fmt.Fprintf(os.Stderr,"Connection error: %v | retry in %s\n",err,backoff)
			select { case <-ctx.Done(): return; case <-time.After(backoff): }
			if backoff<30*time.Second { backoff*=2; if backoff>30*time.Second {backoff=30*time.Second} }
			continue
		}
		backoff=2*time.Second
		if p.Job==nil { select {case <-ctx.Done():return;case <-time.After(2*time.Second):}; continue }
		var output string; var code int
		if confirm(*p.Job) { fmt.Println("Executing..."); output,code=a.runCommand(p.Job.Command) } else { output="Execution rejected locally by the user."; code=125 }
		payload:=resultPayload{ID:p.Job.ID,Output:output,ExitCode:code}
		var sent bool
		for attempt:=1;attempt<=5;attempt++ {
			err=a.request(ctx,"/agent/result",payload,nil)
			if err==nil {sent=true;break}
			fmt.Fprintf(os.Stderr,"Result upload attempt %d failed: %v\n",attempt,err)
			select {case <-ctx.Done():return;case <-time.After(time.Duration(attempt)*2*time.Second):}
		}
		if sent {fmt.Printf("Result sent. Job=%s ExitCode=%d\n",p.Job.ID,code)} else {fmt.Fprintln(os.Stderr,"CRITICAL: result could not be uploaded; keep this window open and check gateway connectivity.")}
	}
}
