using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Threading;
using Marker.Desktop;

static void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
    Console.WriteLine("PASS " + message);
}

var output = Path.GetFullPath(args.FirstOrDefault() ?? "qa-output");
Directory.CreateDirectory(output);
Environment.SetEnvironmentVariable("MARKER_DESKTOP_DATA", Path.Combine(output, "preferences"));
AppBuilder.Configure<App>().UseSkia().UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = false }).SetupWithoutStarting();
Check(Locale.Load("ko").Keys.Order().SequenceEqual(Locale.Load("en").Keys.Order()), "Korean and English resource keys match");
foreach (var valid in new[] { "", "0", "0,2-5", "10-10" }) Check(MainWindow.ValidPageRange(valid), "accept page range " + valid);
foreach (var invalid in new[] { "-1", "5-2", "1,,2", "1;run", "9999999999999", "0-1000001" }) Check(!MainWindow.ValidPageRange(invalid), "reject page range " + invalid);
var window = new MainWindow();
Check(Path.IsPathFullyQualified(window.FindControl<TextBox>("OutputPath")!.Text!), "Default output folder is absolute even without a Documents special folder");
window.Show();
Dispatcher.UIThread.RunJobs();
var force = window.FindControl<CheckBox>("ForceOcr")!;
var disable = window.FindControl<CheckBox>("DisableOcr")!;
var strip = window.FindControl<CheckBox>("StripOcr")!;
force.IsChecked = true;
disable.IsChecked = true;
Check(force.IsChecked == false && disable.IsChecked == true, "Skip OCR clears Force OCR");
Check(strip.IsChecked != true && !strip.IsEnabled, "Skip OCR disables stripping old OCR");
force.IsChecked = true;
Check(disable.IsChecked == false && strip.IsEnabled, "Force OCR clears Skip OCR");
force.IsChecked = false;
window.SetLanguage("ko");
Dispatcher.UIThread.RunJobs();
Check(window.FindControl<Button>("ConvertButton")!.Content?.ToString() == "문서 변환", "Korean UI binding");
window.CaptureRenderedFrame()!.Save(Path.Combine(output, "ui-ko.png"));
window.FindControl<ComboBox>("LanguagePicker")!.SelectedIndex = 1;
Dispatcher.UIThread.RunJobs();
Check(window.FindControl<Button>("ConvertButton")!.Content?.ToString() == "Convert documents", "Live language switch updates UI");
Check(UserSettings.Load().Language == "en", "Language preference persisted");
window.CaptureRenderedFrame()!.Save(Path.Combine(output, "ui-en.png"));
window.Close();
Console.WriteLine("UI QA completed: " + output);
if (args.Length > 1)
{
    var engine = Path.GetFullPath(args[1]);
    var input = Path.GetFullPath(args[2]);
    var request = new ConversionRequest([input], Path.Combine(output, "cancelled-results"), "markdown", "fast", true, false, false, false, false, "");
    using var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(120));
    var cancelled = false;
    try
    {
        Task.Run(() => new EngineRunner().RunAsync(request, item =>
        {
            if (item.Type == "file_started") cancel.CancelAfter(TimeSpan.FromSeconds(8));
        }, cancel.Token, engine)).GetAwaiter().GetResult();
    }
    catch (OperationCanceledException) { cancelled = true; }
    Check(cancelled, "Real offline OCR worker cancellation completes without hanging");
    if (args.Length > 3)
    {
        var successful = new ConversionRequest([Path.GetFullPath(args[3])], Path.Combine(output, "csharp-results"), "markdown", "fast", false, true, false, false, false, "");
        var events = new List<EngineEvent>();
        var exit = Task.Run(() => new EngineRunner().RunAsync(successful, events.Add, CancellationToken.None, engine)).GetAwaiter().GetResult();
        Check(exit == 0 && events.Any(item => item.Type == "file_done" && Directory.Exists(item.Output)), "C# process runner decodes a successful relocated engine result");
    }
}
