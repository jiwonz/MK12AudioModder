// handle commands(named pipe) from python:
// - PROCESS_PROJECT -> convert project's every .bnk into .wav then creates initially and writes index.json
// - PROCESS_BNK -> convert single .bnk into .wav then adds into index.json
//
// uses worker.go to handle a large amount of files (.bnk -> .txtp -> dummy .wem -> delete .txtp, .wem -> .wav -> delete .wem)
// .bnk(.wem) files into .wem
// data files informations:
// - index.json -> [key: bnk name, value: wem id], [key: wem id, value: package path]

using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Versions;
using CUE4Parse.UE4.Objects.Core.Misc;
using System.IO.Pipes;

class Program{
	static void Main(string[] args)
    {
        using (NamedPipeClientStream pipeClient =
            new NamedPipeClientStream(".", "MK12AudioModder", PipeDirection.In))
        {

            // Connect to the pipe or wait until the pipe is available.
            Console.Write("Attempting to connect to pipe...");
            pipeClient.Connect();

            Console.WriteLine("Connected to pipe.");
            Console.WriteLine("There are currently {0} pipe server instances open.",pipeClient.NumberOfServerInstances);
            using (StreamReader sr = new StreamReader(pipeClient))
            {
                // Display the read text to the console
                string? temp;
                while ((temp = sr.ReadLine()) != null)
                {
                    Console.WriteLine("Received from server: {0}", temp);
					if (temp == "test"){
						File.WriteAllText("test.done", "hello python it's c#\n");
					}
                }
            }
        }
    }
}
