namespace UnderYourBed.Animatronic.Models;

public class LipSyncFrame
{
    public double TimeSeconds { get; set; }
    public double MouthOpen01 { get; set; }
}

public class LipSyncData
{
    public List<LipSyncFrame> Frames { get; set; } = new();
}

public class BundleManifest
{
    public DateTime GeneratedUtc { get; set; }
    public string ScriptVersion { get; set; } = string.Empty;
    public BundleSource Source { get; set; } = new();
    public BundleParameters Parameters { get; set; } = new();
    public BundleCounts Counts { get; set; } = new();
    public BundleFiles Files { get; set; } = new();
}

public class BundleSource
{
    public string Type { get; set; } = string.Empty;
    public string? YoutubeUrl { get; set; }
    public string? AudioInput { get; set; }
    public bool OriginalIncluded { get; set; }
    public bool WavCopied { get; set; }
}

public class BundleParameters
{
    public double Fps { get; set; }
    public string Aligner { get; set; } = string.Empty;
    public double EmphasisScale { get; set; }
    public double MinOpen { get; set; }
    public double MaxOpen { get; set; }
}

public class BundleCounts
{
    public int Frames { get; set; }
    public int Words { get; set; }
}

public class BundleFiles
{
    public string Output { get; set; } = string.Empty;
    public string Lyrics { get; set; } = string.Empty;
    public string RhubarbRaw { get; set; } = string.Empty;
    public string Wav { get; set; } = string.Empty;
    public string Original { get; set; } = string.Empty;
}