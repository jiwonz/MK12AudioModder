package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
)

func handler(w http.ResponseWriter, r *http.Request) {
	var name, _ = os.Hostname()
	fmt.Fprintf(w, "<h1>This request was processed by host: %s</h1>\n", name)
}

func main() {
	args := os.Args[1:]
	exec.Command("cue4cli")
	http.HandleFunc("/", handler)
	http.ListenAndServe(":80", nil)
}
