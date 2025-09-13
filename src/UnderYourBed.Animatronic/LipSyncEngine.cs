using System.Text.Json;
using UnderYourBed.Animatronic.Models;

namespace UnderYourBed.Animatronic.LipSync;

public class LipSyncEngine
{
    private readonly List<LipSyncFrame> _frames;
    private DateTime _startTime;
    private bool _isPlaying;

    public LipSyncEngine(string lipSyncFilePath)
    {
        var json = File.ReadAllText(lipSyncFilePath);
        
        // Configure JSON options for case-insensitive property matching
        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };
        
        var lipSyncData = JsonSerializer.Deserialize<LipSyncData>(json, options);
        _frames = lipSyncData?.Frames ?? new List<LipSyncFrame>();
        _startTime = DateTime.UtcNow;
        
        Console.WriteLine($"Loaded {_frames.Count} lip-sync frames from {Path.GetFileName(lipSyncFilePath)}");
        
        if (_frames.Count > 0)
        {
            Console.WriteLine($"First frame: Time={_frames[0].TimeSeconds:F2}s, Mouth={_frames[0].MouthOpen01:F2}");
            Console.WriteLine($"Last frame: Time={_frames[_frames.Count-1].TimeSeconds:F2}s, Mouth={_frames[_frames.Count-1].MouthOpen01:F2}");
        }
    }

    public void Start()
    {
        _startTime = DateTime.UtcNow; // Reset start time when starting
        _isPlaying = true;
        Console.WriteLine("🎬 Lip-sync engine started!");
    }

    public void Stop()
    {
        _isPlaying = false;
    }

    public double GetCurrentMouthPosition()
    {
        if (!_isPlaying) return 0.0;

        var elapsed = DateTime.UtcNow - _startTime;
        var currentTimeSeconds = elapsed.TotalSeconds;

        // Find the appropriate frame based on current time
        var frame = FindFrameAtTime(currentTimeSeconds);
        return frame?.MouthOpen01 ?? 0.0;
    }

    public LipSyncFrame? GetCurrentFrame()
    {
        if (!_isPlaying) return null;

        var elapsed = DateTime.UtcNow - _startTime;
        var currentTimeSeconds = elapsed.TotalSeconds;

        return FindFrameAtTime(currentTimeSeconds);
    }

    private LipSyncFrame? FindFrameAtTime(double timeSeconds)
    {
        if (_frames.Count == 0) return null;

        // Find the frame closest to the current time
        LipSyncFrame? bestFrame = null;
        double bestDistance = double.MaxValue;

        foreach (var frame in _frames)
        {
            var distance = Math.Abs(frame.TimeSeconds - timeSeconds);
            if (distance < bestDistance)
            {
                bestDistance = distance;
                bestFrame = frame;
            }
            
            // If we've passed the current time, we can stop searching
            if (frame.TimeSeconds > timeSeconds) break;
        }

        return bestFrame;
    }

    public void Reset()
    {
        // Reset the start time for a new playback
        _startTime = DateTime.UtcNow;
        _isPlaying = false;
    }
}