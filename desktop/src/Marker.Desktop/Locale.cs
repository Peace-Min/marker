using System.ComponentModel;
using System.Globalization;
using System.Reflection;
using System.Text.Json;

namespace Marker.Desktop;

public sealed class Locale : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    public string Language { get; private set; } = "ko";
    private Dictionary<string, string> _strings = Load("ko");
    public string this[string key] => _strings.GetValueOrDefault(key, key);
    public static Dictionary<string, string> Load(string language)
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream($"Marker.Desktop.Languages.{language}.json")!;
        return JsonSerializer.Deserialize<Dictionary<string, string>>(stream)!;
    }
    public void Set(string language)
    {
        Language = language == "en" ? "en" : "ko";
        _strings = Load(Language);
        CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo(Language);
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs("Item"));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs("Item[]"));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(null));
    }
}

public sealed record UserSettings(string Language = "ko", string OutputFolder = "")
{
    public static string Folder => Environment.GetEnvironmentVariable("MARKER_DESKTOP_DATA")
        ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MarkerDesktop");
    private static string FilePath => Path.Combine(Folder, "settings.json");
    public static UserSettings Load()
    {
        try { return JsonSerializer.Deserialize<UserSettings>(File.ReadAllText(FilePath)) ?? new(); }
        catch (Exception e) when (e is IOException or JsonException or UnauthorizedAccessException) { return new(); }
    }
    public void Save()
    {
        Directory.CreateDirectory(Folder);
        var temp = FilePath + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(this));
        File.Move(temp, FilePath, true);
    }
}
