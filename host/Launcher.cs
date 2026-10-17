// Browser native messaging needs a real executable. All paths are local to this repo.
using System;
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;
class Launcher {
  static int Main(string[] args) {
    try {
      string root = Directory.GetParent(AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar)).FullName;
      var start = new ProcessStartInfo(Path.Combine(root, ".local", "runtime", "Scripts", "python.exe"),
        "-X utf8 -u \"" + Path.Combine(root, "host", "native_host.py") + "\"");
      start.UseShellExecute = false; start.CreateNoWindow = true;
      start.RedirectStandardInput = true; start.RedirectStandardOutput = true;
      start.WorkingDirectory = root;
      var child = Process.Start(start);
      var input = Console.OpenStandardInput(); var output = Console.OpenStandardOutput();
      Task.Run(() => {
        try {
          var buffer = new byte[8192]; int count;
          while ((count = input.Read(buffer, 0, buffer.Length)) > 0) {
            child.StandardInput.BaseStream.Write(buffer, 0, count);
            child.StandardInput.BaseStream.Flush();
          }
          child.StandardInput.Close();
        } catch {}
      });
      child.StandardOutput.BaseStream.CopyTo(output); output.Flush();
      child.WaitForExit(); return child.ExitCode;
    } catch (Exception error) { Console.Error.WriteLine(error.Message); return 1; }
  }
}
