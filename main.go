//go:build windows

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

const gateway = "https://ssh.the-end.shop"

type job struct { ID string `json:"id"`; Command string `json:"command"` }
type pollResponse struct { Job *job `json:"job"`; State string `json:"state"` }
type resultPayload struct { ID string `json:"id"`; Output string `json:"output"`; ExitCode int `json:"exit_code"` }

var httpClient = &http.Client{Timeout: 40*time.Second}

func configPath() (string,error) {
	d,err:=os.UserConfigDir(); if err!=nil{return "",err}
	p:=filepath.Join(d,"MMD-Remote-Agent"); if err=os.MkdirAll(p,0700);err!=nil{return "",err}
	return filepath.Join(p,"device.dat"),nil
}
func loadToken()(string,error){
	p,e:=configPath();if e!=nil{return "",e};b,e:=os.ReadFile(p);if e!=nil{return "",e}
	plain,e:=unprotect(b);if e!=nil{return "",fmt.Errorf("cannot decrypt saved device credential: %w",e)}
	return strings.TrimSpace(string(plain)),nil
}
func saveToken(token string)error{
	p,e:=configPath();if e!=nil{return e};b,e:=protect([]byte(token));if e!=nil{return e}
	tmp:=p+".tmp";if e=os.WriteFile(tmp,b,0600);e!=nil{return e};return os.Rename(tmp,p)
}
func request(ctx context.Context,path string,body any,token string,out any)error{
	var rd io.Reader
	if body!=nil { b,e:=json.Marshal(body);if e!=nil{return e};rd=bytes.NewReader(b) }
	req,e:=http.NewRequestWithContext(ctx,http.MethodPost,gateway+path,rd);if e!=nil{return e}
	req.Header.Set("Accept","application/json");if body!=nil{req.Header.Set("Content-Type","application/json")}
	if token!=""{req.Header.Set("Authorization","Bearer "+token)}
	resp,e:=httpClient.Do(req);if e!=nil{return e};defer resp.Body.Close()
	data,_:=io.ReadAll(io.LimitReader(resp.Body,2<<20))
	if resp.StatusCode<200||resp.StatusCode>=300{return fmt.Errorf("gateway HTTP %d: %s",resp.StatusCode,strings.TrimSpace(string(data)))}
	if out!=nil{return json.Unmarshal(data,out)};return nil
}
func pair(ctx context.Context,code string)error{
	var response struct{DeviceID string `json:"device_id"`;Token string `json:"device_token"`;Paired bool `json:"paired"`}
	if e:=request(ctx,"/agent/pair",map[string]string{"code":code},"",&response);e!=nil{return e}
	if !response.Paired||response.Token==""{return errors.New("gateway did not return a device credential")}
	if e:=saveToken(response.Token);e!=nil{return e}
	fmt.Println("Device paired successfully. Encrypted credential saved for this Windows user.")
	return nil
}
func runCommand(command string)(string,int){
	fmt.Println("\n============================================================")
	fmt.Println("درخواست اجرای فرمان روی این کامپیوتر:")
	fmt.Println("------------------------------------------------------------")
	fmt.Println(command)
	fmt.Println("------------------------------------------------------------")
	fmt.Print("برای اجازه اجرا دقیقاً YES را وارد کن: ")
	var answer string
	fmt.Scanln(&answer)
	if strings.TrimSpace(answer)!="YES"{return "Execution rejected locally by the user.",125}
	ctx,cancel:=context.WithTimeout(context.Background(),10*time.Minute);defer cancel()
	cmd:=syscallCommand(ctx,command)
	out,err:=cmd.CombinedOutput()
	if ctx.Err()!=nil{return string(out)+"\nCommand timed out or was cancelled.",124}
	if err==nil{return string(out),0}
	var exit interface{ ExitCode() int };if errors.As(err,&exit){return string(out),exit.ExitCode()}
	return string(out)+"\n"+err.Error(),1
}

func main(){
	pairCode:=flag.String("pair","","one-time pairing code shown on ssh.the-end.shop")
	flag.Parse()
	if !isAdmin(){fmt.Fprintln(os.Stderr,"ERROR: Run this app as Administrator.");os.Exit(1)}
	ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM);defer stop()
	if *pairCode!="" {if len(*pairCode)!=8{fmt.Fprintln(os.Stderr,"Pairing code must contain 8 digits.");os.Exit(2)};if e:=pair(ctx,*pairCode);e!=nil{fmt.Fprintln(os.Stderr,"Pairing failed:",e);os.Exit(1)};return}
	token,e:=loadToken();if e!=nil||token==""{fmt.Fprintln(os.Stderr,"This app is not paired yet.");fmt.Println("1) Open https://ssh.the-end.shop/");fmt.Println("2) Create a pairing code.");fmt.Println("3) Run: MMD-Remote-Agent.exe --pair 12345678");fmt.Println("Then start this app again.");os.Exit(2)}
	fmt.Println("MMD Remote Agent | AI gateway connection")
	fmt.Println("Gateway:",gateway)
	fmt.Println("Local approval is required for every command. Press Ctrl+C to exit.")
	backoff:=2*time.Second
	for ctx.Err()==nil{
		var poll pollResponse
		e=request(ctx,"/agent/poll",nil,token,&poll)
		if e!=nil{
			if strings.Contains(e.Error(),"HTTP 401")||strings.Contains(e.Error(),"HTTP 403"){fmt.Fprintln(os.Stderr,"Device disconnected or revoked. Pair again from the website.");break}
			fmt.Fprintln(os.Stderr,"Connection:",e,"| retry:",backoff)
			select{case <-ctx.Done():break;case <-time.After(backoff):}
			if backoff<30*time.Second{backoff*=2};continue
		}
		backoff=2*time.Second
		if poll.Job==nil{select{case <-ctx.Done():case <-time.After(2*time.Second):};continue}
		output,code:=runCommand(poll.Job.Command)
		payload:=resultPayload{ID:poll.Job.ID,Output:output,ExitCode:code}
		sent:=false
		for attempt:=0;attempt<3&&ctx.Err()==nil;attempt++{
			e=request(ctx,"/agent/result",payload,token,nil);if e==nil{sent=true;break}
			fmt.Fprintln(os.Stderr,"Result upload failed:",e);select{case <-ctx.Done():case <-time.After(time.Duration(attempt+1)*2*time.Second):}
		}
		if sent{fmt.Println("Result delivered to AI gateway. Job:",poll.Job.ID)}else{fmt.Fprintln(os.Stderr,"CRITICAL: result could not be delivered; keep this window open and check connectivity.")}
	}
	fmt.Println("Agent stopped.")
}