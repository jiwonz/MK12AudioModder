// commands:
// - BNK_TO_WEM <.bnk file paths> -> convert <name>.bnk into dummy wem in <wem id>.wem (deletes .txtp too)
// - PROJECT_BNK_TO_WEM <project folder path>
// - WEM_TO_WAV <.wem file paths> -> convert .wem into .wav then delete .wem
// - PROJECT_WEM_TO_WAV <project folder path>
// - PROJECT_BUILD <project folder path> -> convert project's every .wav into .wem then get package path info from index.json
// then move into correct folder(ex. MK12/Content/WwiseAudio...) and executes unrealpak.exe, so it converts into .pak

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
)

func changeExtension(filePath, newExtension string) string {
	// Get the current extension of the file
	currentExtension := filepath.Ext(filePath)

	// Replace the current extension with the new extension
	newFilePath := filePath[:len(filePath)-len(currentExtension)] + newExtension

	return newFilePath
}

func bnkToWem(bnk string, wg *sync.WaitGroup) {
	defer wg.Done()

	dir := filepath.Dir(bnk)

	//cmd := exec.Command("./pypy/pypy", "wwiser.pyz", "-g", bnk, "-go", dir)

	// Find and read txtp file
	var txtpPath string
	items, err := os.ReadDir(dir)
	if err != nil {
		fmt.Printf("Error reading directory: %s\n", err)
		return
	}

	for _, item := range items {
		if item.IsDir() || filepath.Ext(item.Name()) != ".txtp" {
			continue
		}
		if strings.HasPrefix(item.Name(), strings.TrimSuffix(filepath.Base(bnk), filepath.Ext(bnk))) {
			txtpPath = filepath.Join(dir, item.Name())
		}
	}

	if txtpPath != "" {
		content, err := os.ReadFile(txtpPath)
		if err != nil {
			fmt.Printf("Error reading file: %s\n", err)
			return
		}
		re := regexp.MustCompile(`Source (\d+)`)
		match := re.FindStringSubmatch(string(content))
		if len(match) > 1 {
			wemSource := match[1]
			// fmt.Println("Source number:", wemSource)
			file, err := os.Create(filepath.Join(dir, fmt.Sprintf("%s.wem", wemSource)))
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			defer file.Close()
		} else {
			fmt.Println("Source number not found.")
		}

		if err := os.Remove(txtpPath); err != nil {
			fmt.Printf("Error removing file: %s\n", err)
		}
	}
}

func main() {
	args := os.Args[1:]
	switch args[0] {
	case "BNK_TO_WEM":
		var wg sync.WaitGroup
		cmd := exec.Command("./wwiser.exe", "-g", strings.Join(args[1:len(args)], " "), "-go", filepath.Dir(args[1]))
		if err := cmd.Run(); err != nil {
			fmt.Printf("Error executing wwiser: %s\n", err)
			return
		}
		for i := 1; i <= len(args)-1; i++ {
			wg.Add(1)
			go bnkToWem(args[i], &wg)
		}
		wg.Wait()
	case "PROJECT_BNK_TO_WEM":
		var wg sync.WaitGroup
		dir := args[1]
		items, err := os.ReadDir(dir)
		if err != nil {
			fmt.Printf("Error reading directory: %s\n", err)
			return
		}
		bnks := []string{}
		for _, item := range items {
			if item.IsDir() || filepath.Ext(item.Name()) != ".bnk" {
				continue
			}
			bnks = append(bnks, fmt.Sprintf("%s", filepath.Join(dir, item.Name())))
		}
		// fmt.Println(strings.Join(bnks, " "))
		// fmt.Println(dir)
		//cmd := exec.Command("./wwiser.bat", "-g", strings.Join(bnks, " "), "-go", dir)
		// cmd := exec.Command("./wwiser.bat")

		cmd := fmt.Sprintf(".\\wwiser2.bat -g %s -go %s", strings.Join(bnks, " "), dir)

		err = exec.Command("cmd", "/C", cmd).Run()
		// output, err := exec.Command(".\\pypy\\pypy.exe", ".\\wwiser.pyz", "-g", strings.Join(bnks, " "), "-go", dir).Output()
		if err != nil {
			fmt.Println("Error executing command:", err)
			return
		}

		// if err := cmd.Run(); err != nil {
		// 	fmt.Printf("Error executing wwiser: %s\n", err)
		// 	return
		// }
		for _, item := range items {
			if item.IsDir() || filepath.Ext(item.Name()) != ".bnk" {
				continue
			}
			wg.Add(1)
			//fmt.Println(filepath.Join(args[1], item.Name()))
			go bnkToWem(filepath.Join(dir, item.Name()), &wg)
		}
		wg.Wait()
	}
}
