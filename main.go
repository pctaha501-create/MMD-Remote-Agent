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
    "path/filepath"
    "strings"
    "syscall"
    "time"
)

const gateway = "https://ssh.the-end.shop"
type job struct { ID string; Command string }
type pollResponse struct { Job *job; State string }
type agent struct { token string; client *http.Client }

func newAgent(token string) *agent {
    return &agent{token: token, client: &http.Client{Timeout: 35*time.Second, Transport: &http.Transport{
        Proxy: http.ProxyFromEnvironment, MaxIdleConns: 2, IdleConnTimeout: 20*time.Second, TLSHandshakeTimeout: 10*time.Second,
    }}}
}
func tokenPath() (string, error) {
    dir, err := os.UserConfigDir()
    if err != nil { return "", err }
    return filepath.Join(dir, "MMD-Remote-Agent", "device.dat"), nil
}
func loadSavedToken() string {
    path, err := tokenPath(); if err != nil { return "" }
    encrypted, err := os.ReadFile(path); if err != nil { return "" }
    plain, err := unprotect(encrypted); if err != nil { return "" }
    return strings.TrimSpace(string(plain))
}
func saveToken(token string) error {
    path, err := tokenPath(); if err != nil { return err }
    encrypted, err := protect([]byte(token)); if err != nil { return err }
    if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil { return err }
    return os.WriteFile(path, encrypted, 0600)
}
func clearSavedToken() {
    path, err := tokenPath(); if err == nil { _ = os.Remove(path) }
}
func pairWithCode(code string) (string, error) {
    body, err := json.Marshal(map[string]string{"code": code}); if err != nil { return "", err }
    ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second); defer cancel()
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, gateway+"/agent/pair", bytes.NewReader(body))
    if err != nil { return "", err }
    req.Header.Set("Accept", "application/json")
    req.Header.Set("Content-Type", "application/json")
    resp, err := (&http.Client{Timeout: 20*time.Second}).Do(req)
    if err != nil { return "", err }
    defer resp.Body.Close()
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        data, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
        return "", fmt.Errorf("pairing failed (HTTP %d): %s", resp.StatusCode, strings.TrimSpace(string(data)))
    }
    var data map[string]any
    if err := json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(&data); err != nil { return "", err }
    token, _ := data["device_token"].(string)
    paired, _ := data["paired"].(bool)
    if !paired || token == "" { return "", errors.New("the server did not return a valid device token") }
    return token, nil
}
func promptForCode() (string, error) {
    reader := bufio.NewReader(os.Stdin)
    for {
        fmt.Print("Enter Connection Code: ")
        line, err := reader.ReadString('\n')
        if err != nil && len(line) == 0 { return "", err }
        code := strings.TrimSpace(line)
        valid := len(code) == 8
        for _, ch := range code { if ch < '0' || ch > '9' { valid = false; break } }
        if !valid {
            fmt.Println("Please enter the 8-digit code shown on the website.")
            if err != nil { return "", err }
            continue
        }
        fmt.Println("Connecting to server...")
        token, pairErr := pairWithCode(code)
        if pairErr != nil {
            fmt.Println("Connection failed:", pairErr)
            fmt.Println("Generate a fresh code on the website and try again.")
            if err != nil { return "", err }
            continue
        }
        fmt.Println("Connection code accepted.")
        return token, nil
    }
}
func (a *agent) request(ctx context.Context, path string, body any, out any) error {
    var rd io.Reader
    if body != nil {
        b, err := json.Marshal(body); if err != nil { return err }
        rd = bytes.NewReader(b)
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, gateway+path, rd)
    if err != nil { return err }
    req.Header.Set("Authorization", "Bearer "+a.token)
    req.Header.Set("Accept", "application/json")
    if body != nil { req.Header.Set("Content-Type", "application/json") }
    resp, err := a.client.Do(req); if err != nil { return err }
    defer resp.Body.Close()
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        data, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
        return fmt.Errorf("gateway returned HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(data)))
    }
    if out != nil { return json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(out) }
    _, err = io.Copy(io.Discard, resp.Body)
    return err
}
func (a *agent) runCommand(command string) (string, int) {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute); defer cancel()
    cmd := exec.CommandContext(ctx, "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command)
    var out bytes.Buffer
    cmd.Stdout, cmd.Stderr = &out, &out
    err := cmd.Run()
    if ctx.Err() != nil { return out.String()+"\nCommand timed out or was cancelled.", 124 }
    if err == nil { return out.String(), 0 }
    var exitErr *exec.ExitError
    if errors.As(err, &exitErr) { return out.String(), exitErr.ExitCode() }
    return out.String()+"\n"+err.Error(), 1
}
func confirm(j job) bool {
    fmt.Println("\n============================================================")
    fmt.Println("NEW COMMAND — LOCAL APPROVAL REQUIRED")
    fmt.Println("Job:", j.ID)
    fmt.Println("------------------------------------------------------------")
    fmt.Println(j.Command)
    fmt.Println("------------------------------------------------------------")
    fmt.Print("Type YES to execute this command; anything else rejects it: ")
    line, _ := bufio.NewReader(os.Stdin).ReadString('\n')
    return strings.EqualFold(strings.TrimSpace(line), "YES")
}
func main() {
    fmt.Println("============================================================")
    fmt.Println("                 MMD REMOTE AGENT")
    fmt.Println("============================================================")
    if !isAdmin() {
        fmt.Fprintln(os.Stderr, "ERROR: Run this application as Administrator.")
        os.Exit(1)
    }
    fmt.Println("Administrator: OK")
    token := loadSavedToken()
    if token == "" {
        var err error
        token, err = promptForCode()
        if err != nil { fmt.Fprintln(os.Stderr, "ERROR:", err); os.Exit(2) }
        if err := saveToken(token); err != nil {
            fmt.Fprintln(os.Stderr, "WARNING: Could not securely save the device token:", err)
            fmt.Println("You may need to enter a new connection code next time.")
        }
    } else { fmt.Println("Saved secure connection found.") }
    a := newAgent(token)
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()
    fmt.Println("Gateway:", gateway)
    fmt.Println("Waiting for MCP commands... (Ctrl+C to exit)")
    backoff := 2*time.Second
    for {
        if ctx.Err() != nil { fmt.Println("\nDisconnected."); return }
        var p pollResponse
        err := a.request(ctx, "/agent/poll", nil, &p)
        if err != nil {
            if strings.Contains(err.Error(), "HTTP 401") {
                fmt.Println("The saved connection is no longer valid.")
                clearSavedToken()
                newToken, pairErr := promptForCode()
                if pairErr != nil { fmt.Fprintln(os.Stderr, "ERROR:", pairErr); return }
                a.token = newToken
                if saveErr := saveToken(newToken); saveErr != nil {
                    fmt.Fprintln(os.Stderr, "WARNING: Could not securely save the device token:", saveErr)
                }
                backoff = 2*time.Second
                continue
            }
            fmt.Fprintf(os.Stderr, "Connection error: %v | retry in %s\n", err, backoff)
            select { case <-ctx.Done(): return; case <-time.After(backoff): }
            if backoff < 30*time.Second { backoff *= 2; if backoff > 30*time.Second { backoff = 30*time.Second } }
            continue
        }
        backoff = 2*time.Second
        if p.Job == nil {
            select { case <-ctx.Done(): return; case <-time.After(2*time.Second): }
            continue
        }
        var output string
        var exitCode int
        if confirm(*p.Job) {
            fmt.Println("Executing...")
            output, exitCode = a.runCommand(p.Job.Command)
        } else { output, exitCode = "Execution rejected locally by the user.", 125 }
        payload := map[string]any{"id":p.Job.ID, "output":output, "exit_code":exitCode}
        sent := false
        for attempt := 1; attempt <= 5; attempt++ {
            err = a.request(ctx, "/agent/result", payload, nil)
            if err == nil { sent = true; break }
            fmt.Fprintf(os.Stderr, "Result upload attempt %d failed: %v\n", attempt, err)
            select { case <-ctx.Done(): return; case <-time.After(time.Duration(attempt)*2*time.Second): }
        }
        if sent { fmt.Printf("Result sent. Job=%s ExitCode=%d\n", p.Job.ID, exitCode) } else {
            fmt.Fprintln(os.Stderr, "CRITICAL: result could not be uploaded; keep this window open and check gateway connectivity.")
        }
    }
}
