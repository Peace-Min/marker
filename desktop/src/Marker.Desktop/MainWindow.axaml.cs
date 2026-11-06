using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Text.RegularExpressions;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;

namespace Marker.Desktop;

public partial class MainWindow : Window
{
    public Locale L { get; } = new();
    public ObservableCollection<string> Files { get; } = new();
    private CancellationTokenSource? _conversion;
    private bool _initializing = true;
    private string? _lastOutput;
    private string _state = "Ready";
    public MainWindow()
    {
        InitializeComponent();
        DataContext = this;
        var settings = UserSettings.Load();
        L.Set(settings.Language);
        LanguagePicker.SelectedIndex = L.Language == "en" ? 1 : 0;
        var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        if (string.IsNullOrWhiteSpace(documents)) documents = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Documents");
        OutputPath.Text = string.IsNullOrWhiteSpace(settings.OutputFolder) || !Path.IsPathFullyQualified(settings.OutputFolder)
            ? Path.Combine(documents, "Marker Results") : settings.OutputFolder;
        Files.CollectionChanged += (_, _) => EmptyLabel.IsVisible = Files.Count == 0;
        Closing += OnClosing;
        _initializing = false;
    }

    public void SetLanguage(string language)
    {
        L.Set(language);
        Status.Text = L[_state];
    }
    private void LanguageChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (_initializing) return;
        SetLanguage(LanguagePicker.SelectedIndex == 1 ? "en" : "ko");
        SaveSettings();
    }
    private void SaveSettings()
    {
        try { new UserSettings(L.Language, OutputPath.Text ?? "").Save(); }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException) { Log($"{L["SaveError"]}: {e.Message}"); }
    }
    private async void AddFiles(object? sender, RoutedEventArgs e)
    {
        var files = await StorageProvider.OpenFilePickerAsync(new()
        {
            Title = L["AddFiles"], AllowMultiple = true,
            FileTypeFilter = [new("PDF / Images") { Patterns = ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp", "*.webp"] }]
        });
        foreach (var file in files)
            if (file.TryGetLocalPath() is { } path && !Files.Contains(path)) Files.Add(path);
    }
    private void ClearFiles(object? sender, RoutedEventArgs e) => Files.Clear();
    private async void ChooseFolder(object? sender, RoutedEventArgs e)
    {
        var folders = await StorageProvider.OpenFolderPickerAsync(new() { Title = L["Output"], AllowMultiple = false });
        if (folders.FirstOrDefault()?.TryGetLocalPath() is { } path) { OutputPath.Text = path; SaveSettings(); }
    }
    private void OcrChanged(object? sender, RoutedEventArgs e)
    {
        if (sender == ForceOcr && ForceOcr.IsChecked == true && DisableOcr is not null) DisableOcr.IsChecked = false;
        if (sender == DisableOcr && DisableOcr?.IsChecked == true && ForceOcr is not null)
        {
            ForceOcr.IsChecked = false;
            if (StripOcr is not null) StripOcr.IsChecked = false;
        }
        if (StripOcr is not null) StripOcr.IsEnabled = DisableOcr?.IsChecked != true;
    }
    public static bool ValidPageRange(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return true;
        if (!Regex.IsMatch(value, @"^\d+(-\d+)?(,\d+(-\d+)?)*$")) return false;
        foreach (var range in value.Split(','))
        {
            var parts = range.Split('-');
            if (!int.TryParse(parts[0], out var first) || first > 1000000) return false;
            if (parts.Length == 2 && (!int.TryParse(parts[1], out var last) || last < first || last > 1000000)) return false;
        }
        return true;
    }
    private async void ConvertFiles(object? sender, RoutedEventArgs e)
    {
        if (_conversion is not null) return;
        if (Files.Count == 0) { Log(L["ChooseInput"]); return; }
        if (string.IsNullOrWhiteSpace(OutputPath.Text)) { Log(L["ChooseOutput"]); return; }
        if (!ValidPageRange(PageRange.Text ?? "")) { Log(L["InvalidRange"]); return; }
        if (!EngineRunner.IsAvailable) { Log(L["MissingEngine"]); return; }
        var request = new ConversionRequest(Files.ToArray(), OutputPath.Text!,
            new[] { "markdown", "json", "html", "chunks" }[FormatPicker.SelectedIndex], ModePicker.SelectedIndex == 1 ? "balanced" : "fast",
            ForceOcr.IsChecked == true, DisableOcr.IsChecked == true, StripOcr.IsChecked == true,
            Headers.IsChecked == true, DebugFiles.IsChecked == true, PageRange.Text ?? "");
        _conversion = new();
        SetBusy(true);
        SetState("Starting");
        SaveSettings();
        try
        {
            var exit = await new EngineRunner().RunAsync(request, item => Dispatcher.UIThread.Post(() => Receive(item)), _conversion.Token);
            SetState(exit == 0 ? "Completed" : "Failed");
            if (exit != 0) Log(L["CompleteWithErrors"]);
        }
        catch (OperationCanceledException) { SetState("Cancelled"); Log(L["Cancelled"]); }
        catch (Exception error) { SetState("Failed"); Log(error.Message); }
        finally { _conversion.Dispose(); _conversion = null; SetBusy(false); }
    }
    private void Receive(EngineEvent item)
    {
        if (item.Type == "file_started") { SetState("Processing"); Log($"{L["Processing"]}: {item.File}"); }
        if (item.Type == "file_done") { _lastOutput = item.Output; Log($"{L["Completed"]}: {item.Output}"); }
        if (item.Type is "file_error" or "error") Log($"{L["Failed"]}: {item.File} {item.Message}");
        if (item.Type == "log" && item.Message is not null) Log(item.Message);
        if (item.Total > 0) { Progress.IsIndeterminate = false; Progress.Value = 100d * item.Done / item.Total; }
    }
    private void SetState(string state) { _state = state; Status.Text = L[state]; }
    private void SetBusy(bool busy)
    {
        AddButton.IsEnabled = ClearButton.IsEnabled = BrowseButton.IsEnabled = OutputPath.IsEnabled = OptionsPanel.IsEnabled = ConvertButton.IsEnabled = !busy;
        CancelButton.IsEnabled = busy;
        Progress.IsIndeterminate = busy;
        if (busy) Progress.Value = 0;
    }
    private void Log(string message)
    {
        var text = Activity.Text ?? "";
        if (text.Length > 30000) text = text[^20000..];
        Activity.Text = text + $"[{DateTime.Now:HH:mm:ss}] {message}{Environment.NewLine}";
        Activity.CaretIndex = Activity.Text.Length;
    }
    private void CancelConversion(object? sender, RoutedEventArgs e) => _conversion?.Cancel();
    private void OpenOutput(object? sender, RoutedEventArgs e) => OpenPath(_lastOutput ?? OutputPath.Text ?? "");
    private void OpenLogs(object? sender, RoutedEventArgs e) => OpenPath(Path.Combine(UserSettings.Folder, "runs"));
    private void OpenWiki(object? sender, RoutedEventArgs e) => OpenPath(Path.Combine(AppContext.BaseDirectory, "Wiki", L.Language == "en" ? "README.en.html" : "README.html"));
    private void OpenPath(string path)
    {
        try { if (Directory.Exists(path) || File.Exists(path)) Process.Start(new ProcessStartInfo(path) { UseShellExecute = true }); }
        catch (Exception error) { Log(error.Message); }
    }
    private async void OnClosing(object? sender, WindowClosingEventArgs e)
    {
        if (_conversion is null) { SaveSettings(); return; }
        e.Cancel = true;
        var dialog = new Window { Title = L["Title"], Width = 430, Height = 170, CanResize = false, WindowStartupLocation = WindowStartupLocation.CenterOwner };
        var yes = new Button { Content = L["Yes"] };
        var no = new Button { Content = L["No"] };
        dialog.Content = new StackPanel { Margin = new(20), Spacing = 18, Children = { new TextBlock { Text = L["ConfirmExit"] }, new StackPanel { Orientation = Avalonia.Layout.Orientation.Horizontal, Spacing = 10, Children = { yes, no } } } };
        yes.Click += (_, _) => { _conversion?.Cancel(); dialog.Close(true); };
        no.Click += (_, _) => dialog.Close(false);
        if (await dialog.ShowDialog<bool>(this))
        {
            while (_conversion is not null) await Task.Delay(50);
            Close();
        }
    }
}
