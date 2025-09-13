using System.Diagnostics;

namespace UnderYourBed.Animatronic.Audio;

public class AudioPlayer : IDisposable
{
    private Process? _audioProcess;
    private bool _isPlaying;
    private readonly object _lock = new();
    private string? _currentAudioFile;
    private CancellationTokenSource? _cancellationTokenSource;

    public event EventHandler? PlaybackStarted;
    public event EventHandler? PlaybackStopped;

    public bool IsPlaying 
    { 
        get 
        { 
            lock (_lock) 
            { 
                return _isPlaying; 
            } 
        } 
    }

    public async Task LoadAudioFileAsync(string filePath)
    {
        if (!File.Exists(filePath))
        {
            throw new FileNotFoundException($"Audio file not found: {filePath}");
        }

        await Task.Run(() =>
        {
            lock (_lock)
            {
                Stop();
                _currentAudioFile = filePath;
                Console.WriteLine($"Audio file loaded: {Path.GetFileName(filePath)}");
            }
        });
    }

    public async Task PlayAsync()
    {
        lock (_lock)
        {
            if (_currentAudioFile == null)
            {
                throw new InvalidOperationException("No audio file loaded");
            }

            if (_isPlaying)
            {
                return;
            }

            _isPlaying = true;
        }

        PlaybackStarted?.Invoke(this, EventArgs.Empty);

        try
        {
            _cancellationTokenSource = new CancellationTokenSource();
            
            // Use ffplay to play the audio file through USB audio device
            var startInfo = new ProcessStartInfo
            {
                FileName = "ffplay",
                Arguments = $"-nodisp -autoexit -loglevel quiet -af \"aformat=channel_layouts=stereo\" -ac 2 \"{_currentAudioFile}\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            // Set environment to use USB audio device (card 0)
            startInfo.Environment["ALSA_AUDIO_DEVICE"] = "hw:0,0";
            startInfo.Environment["PULSE_AUDIO_DEVICE"] = "alsa_output.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-stereo";

            _audioProcess = new Process { StartInfo = startInfo };
            _audioProcess.EnableRaisingEvents = true;
            _audioProcess.Exited += OnProcessExited;
            
            _audioProcess.Start();
            Console.WriteLine("Playback started...");
            
            // Wait for process to complete
            await _audioProcess.WaitForExitAsync(_cancellationTokenSource.Token);
        }
        catch (OperationCanceledException)
        {
            // Playback was stopped
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Playback error: {ex.Message}");
        }
        finally
        {
            lock (_lock)
            {
                _isPlaying = false;
            }
            PlaybackStopped?.Invoke(this, EventArgs.Empty);
        }
    }

    public void Play()
    {
        _ = Task.Run(async () => await PlayAsync());
    }

    public void Stop()
    {
        lock (_lock)
        {
            if (_isPlaying && _audioProcess != null && !_audioProcess.HasExited)
            {
                try
                {
                    _cancellationTokenSource?.Cancel();
                    _audioProcess.Kill();
                    _audioProcess.WaitForExit(1000);
                    Console.WriteLine("Playback stopped");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error stopping playback: {ex.Message}");
                }
            }
            _isPlaying = false;
        }
        PlaybackStopped?.Invoke(this, EventArgs.Empty);
    }

    private void OnProcessExited(object? sender, EventArgs e)
    {
        lock (_lock)
        {
            _isPlaying = false;
        }
        PlaybackStopped?.Invoke(this, EventArgs.Empty);
        Console.WriteLine("Playback finished");
    }

    public void Dispose()
    {
        Stop();
        _audioProcess?.Dispose();
        _cancellationTokenSource?.Dispose();
    }
}