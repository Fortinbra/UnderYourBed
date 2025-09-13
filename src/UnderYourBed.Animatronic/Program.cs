using UnderYourBed.Animatronic.Audio;

namespace UnderYourBed.Animatronic;

class SimpleAudioTest
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Simple M4A Audio Test");
        Console.WriteLine("====================");

        var bundlePath = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059";
        var audioPath = Path.Combine(bundlePath, "original.m4a");

        if (!File.Exists(audioPath))
        {
            Console.WriteLine($"Error: Audio file not found at {audioPath}");
            return;
        }

        using var audioPlayer = new AudioPlayer();
        
        audioPlayer.PlaybackStarted += (s, e) => Console.WriteLine("🎵 Audio started playing!");
        audioPlayer.PlaybackStopped += (s, e) => Console.WriteLine("🔇 Audio stopped.");

        try
        {
            Console.WriteLine($"Loading: {Path.GetFileName(audioPath)}");
            await audioPlayer.LoadAudioFileAsync(audioPath);
            
            Console.WriteLine("Starting playback for 5 seconds...");
            audioPlayer.Play();
            
            // Let it play for 5 seconds
            await Task.Delay(5000);
            
            Console.WriteLine("Stopping playback...");
            audioPlayer.Stop();
            
            // Wait a moment for cleanup
            await Task.Delay(1000);
            
            Console.WriteLine("✅ Audio test completed successfully!");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
        }
    }
}