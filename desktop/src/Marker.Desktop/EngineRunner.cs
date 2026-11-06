using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace Marker.Desktop;

public sealed record ConversionRequest(string[] Files, string Output, string Format, string Mode,
    bool ForceOcr, bool DisableOcr, bool StripExistingOcr, bool KeepHeaders, bool Debug, string PageRange);
public sealed record EngineEvent(string Type, string? File = null, string? Message = null, string? Output = null, int Done = 0, int Total = 0);

public sealed class EngineRunner
{
    public static string EngineRoot => Path.Combine(AppContext.BaseDirectory, "engine");
    public static string PythonPath => OperatingSystem.IsWindows()
        ? Path.Combine(EngineRoot, "python", "python.exe") : Path.Combine(EngineRoot, "python", "bin", "python3");
    public static bool IsAvailable => File.Exists(PythonPath) && File.Exists(Path.Combine(EngineRoot, "worker.py"));

    public async Task<int> RunAsync(ConversionRequest request, Action<EngineEvent> report, CancellationToken cancellation, string? engineRoot = null)
    {
        var root = engineRoot ?? EngineRoot;
        var python = OperatingSystem.IsWindows() ? Path.Combine(root, "python", "python.exe") : Path.Combine(root, "python", "bin", "python3");
        var run = Path.Combine(UserSettings.Folder, "runs", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(run);
        var requestPath = Path.Combine(run, "request.json");
        await File.WriteAllTextAsync(requestPath, JsonSerializer.Serialize(request, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower }), cancellation);
        var start = new ProcessStartInfo(python)
        {
            WorkingDirectory = run, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
        };
        start.ArgumentList.Add("-u");
        start.ArgumentList.Add(Path.Combine(root, "worker.py"));
        start.ArgumentList.Add("--request");
        start.ArgumentList.Add(requestPath);
        start.Environment["PYTHONNOUSERSITE"] = "1";
        start.Environment["PYTHONUTF8"] = "1";
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        start.Environment["PYTHONDONTWRITEBYTECODE"] = "1";
        start.Environment.Remove("PYTHONPATH");
        start.Environment.Remove("PYTHONHOME");
        start.Environment["MARKER_RUNTIME_DIR"] = run;
        using var process = Process.Start(start) ?? throw new IOException("Could not start Python");
        using var registration = cancellation.Register(() =>
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
            catch (InvalidOperationException) { }
        });
        await using var log = new StreamWriter(Path.Combine(run, "engine.log"), append: false, Encoding.UTF8);
        var stderr = Task.Run(async () =>
        {
            while (await process.StandardError.ReadLineAsync() is { } line)
                await log.WriteLineAsync(line);
        });
        while (await process.StandardOutput.ReadLineAsync() is { } line)
        {
            try
            {
                var item = JsonSerializer.Deserialize<EngineEvent>(line, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                if (item is not null) report(item);
            }
            catch (JsonException) { report(new("log", Message: line)); }
        }
        await process.WaitForExitAsync(CancellationToken.None);
        await stderr;
        cancellation.ThrowIfCancellationRequested();
        return process.ExitCode;
    }
}
