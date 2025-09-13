using UnderYourBed.Animatronic.Audio;
using UnderYourBed.Animatronic.Hardware;
using UnderYourBed.Animatronic.LipSync;

namespace UnderYourBed.Animatronic;

class Program
{
    static async Task Main(string[] args)
    {
        if (args.Length > 0 && args[0].ToLower() == "servo")
        {
            await RunServoTest();
        }
        else if (args.Length > 0 && args[0].ToLower() == "combo")
        {
            await RunComboTest();
        }
        else if (args.Length > 0 && args[0].ToLower() == "servoonly")
        {
            await RunServoOnlyTest();
        }
        else if (args.Length > 0 && args[0].ToLower() == "lipsync")
        {
            await RunLipSyncTest();
        }
        else if (args.Length > 0 && args[0].ToLower() == "lipdiag")
        {
            await RunLipSyncDiagnostics();
        }
        else
        {
            await RunAudioTest();
        }
    }

    static async Task RunServoOnlyTest()
    {
        Console.WriteLine("Simple Servo Movement Test");
        Console.WriteLine("==========================");

        using var servo = new ServoController(0);
        
        Console.WriteLine("Testing basic servo movements...");
        
        var positions = new[] { 0.0, 0.25, 0.5, 0.75, 1.0, 0.5 };
        var names = new[] { "0°", "45°", "90°", "135°", "180°", "90°" };
        
        for (int i = 0; i < positions.Length; i++)
        {
            Console.WriteLine($"Moving to {names[i]} (position {positions[i]})");
            servo.SetPosition(positions[i]);
            await Task.Delay(2000);
        }
        
        servo.Stop();
        Console.WriteLine("✅ Simple servo test completed!");
    }

    static async Task RunDebugTest()
    {
        Console.WriteLine("Debug Test: Servo First, Then Audio");
        Console.WriteLine("===================================");

        var bundlePath = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059";
        var audioPath = Path.Combine(bundlePath, "original.m4a");

        using var servo = new ServoController(0);
        using var audioPlayer = new AudioPlayer();

        Console.WriteLine("Phase 1: Testing servo movement BEFORE starting audio...");
        
        // Test servo movement first
        servo.SetPosition(0.2);
        await Task.Delay(2000);
        servo.SetPosition(0.8);
        await Task.Delay(2000);
        servo.SetPosition(0.5);
        await Task.Delay(2000);
        
        Console.WriteLine("Phase 1 complete. Did the servo move? (Press Enter to continue)");
        Console.ReadLine();
        
        Console.WriteLine("Phase 2: Loading audio (servo should still be responsive)...");
        await audioPlayer.LoadAudioFileAsync(audioPath);
        
        // Test servo after audio is loaded but not playing
        servo.SetPosition(0.1);
        await Task.Delay(2000);
        servo.SetPosition(0.9);
        await Task.Delay(2000);
        
        Console.WriteLine("Phase 2 complete. Did the servo move after audio was loaded? (Press Enter to continue)");
        Console.ReadLine();
        
        Console.WriteLine("Phase 3: Starting audio playback while moving servo...");
        audioPlayer.Play();
        
        // Test servo while audio is playing
        for (int i = 0; i < 5; i++)
        {
            Console.WriteLine($"Servo movement {i + 1}/5 during audio playback");
            servo.SetPosition(i % 2 == 0 ? 0.2 : 0.8);
            await Task.Delay(3000);
        }
        
        audioPlayer.Stop();
        servo.Stop();
        
        Console.WriteLine("Debug test complete!");
    }

    static async Task RunLipSyncTest()
    {
        Console.WriteLine("Real Lip-Sync Animation Test");
        Console.WriteLine("============================");

        var bundlePath = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059";
        var audioPath = Path.Combine(bundlePath, "original.m4a");
        var lipSyncPath = Path.Combine(bundlePath, "song.lipsync.json");

        if (!File.Exists(audioPath))
        {
            Console.WriteLine($"Error: Audio file not found at {audioPath}");
            return;
        }

        if (!File.Exists(lipSyncPath))
        {
            Console.WriteLine($"Error: Lip-sync file not found at {lipSyncPath}");
            return;
        }

        using var audioPlayer = new AudioPlayer();
        using var servo = new ServoController(0);
        var lipSyncEngine = new LipSyncEngine(lipSyncPath);

        // Set up event handlers
        audioPlayer.PlaybackStarted += (s, e) => Console.WriteLine("🎵 Audio and lip-sync started!");
        audioPlayer.PlaybackStopped += (s, e) => Console.WriteLine("🔇 Audio and lip-sync stopped.");

        try
        {
            Console.WriteLine("Loading audio and lip-sync data...");
            await audioPlayer.LoadAudioFileAsync(audioPath);
            
            Console.WriteLine("Starting synchronized audio + lip-sync animation...");
            Console.WriteLine("🎭 This will run for the full 2.5 minute performance!");
            Console.WriteLine("Watch the servo move in sync with the audio!");
            
            // Start both audio and lip-sync
            audioPlayer.Play();
            lipSyncEngine.Start();
            
            var startTime = DateTime.UtcNow;
            
            // Update servo position based on lip-sync data
            var updateTask = Task.Run(async () =>
            {
                var lastPosition = -1.0;
                var frameCount = 0;
                
                while (audioPlayer.IsPlaying)
                {
                    var currentFrame = lipSyncEngine.GetCurrentFrame();
                    if (currentFrame != null)
                    {
                        frameCount++;
                        
                        // Only update servo if position changed significantly (avoid jitter)
                        var newPosition = currentFrame.MouthOpen01;
                        if (Math.Abs(newPosition - lastPosition) > 0.01) // 1% threshold (was 5%)
                        {
                            servo.SetPosition(newPosition);
                            lastPosition = newPosition;
                        }
                        
                        // Show progress every 10 seconds
                        if (frameCount % 600 == 0) // ~10 seconds at 60fps
                        {
                            var elapsed = DateTime.UtcNow - startTime;
                            Console.WriteLine($"🎵 {elapsed.TotalSeconds:F0}s elapsed - Mouth position: {newPosition:F2}");
                        }
                    }
                    
                    // Update at ~60 FPS for smooth movement
                    await Task.Delay(16);
                }
                
                Console.WriteLine($"🎭 Animation completed! Processed {frameCount} frames");
            });
            
            // Wait for audio to finish (with timeout for safety)
            var timeout = TimeSpan.FromMinutes(3); // 3 minute timeout
            var endTime = DateTime.UtcNow + timeout;
            
            while (audioPlayer.IsPlaying && DateTime.UtcNow < endTime)
            {
                await Task.Delay(1000);
                var elapsed = DateTime.UtcNow - startTime;
                
                // Show progress every 30 seconds
                if ((int)elapsed.TotalSeconds % 30 == 0 && elapsed.TotalSeconds > 0)
                {
                    Console.WriteLine($"🕐 Performance progress: {elapsed.TotalSeconds:F0}/151 seconds");
                }
            }
            
            // Stop everything
            lipSyncEngine.Stop();
            await updateTask;
            servo.SetCenter();
            await Task.Delay(1000);
            servo.Stop();
            
            Console.WriteLine("✅ Lip-sync animation completed successfully!");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
        }
    }

    static async Task RunLipSyncDiagnostics()
    {
        Console.WriteLine("Lip-Sync Diagnostics");
        Console.WriteLine("====================");

        var bundlePath = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059";
        var lipSyncPath = Path.Combine(bundlePath, "song.lipsync.json");

        var lipSyncEngine = new LipSyncEngine(lipSyncPath);
        using var servo = new ServoController(0);

        Console.WriteLine("Testing lip-sync data processing without audio...");
        
        lipSyncEngine.Start();
        
        // Test for 30 seconds to see the values
        var testDuration = TimeSpan.FromSeconds(30);
        var startTime = DateTime.UtcNow;
        var lastMouthValue = -1.0;
        
        while (DateTime.UtcNow - startTime < testDuration)
        {
            var currentFrame = lipSyncEngine.GetCurrentFrame();
            if (currentFrame != null)
            {
                var mouthValue = currentFrame.MouthOpen01;
                
                // Show significant changes
                if (Math.Abs(mouthValue - lastMouthValue) > 0.01)
                {
                    Console.WriteLine($"Time: {currentFrame.TimeSeconds:F2}s, Mouth: {mouthValue:F3} -> Servo: {mouthValue:F2}");
                    servo.SetPosition(mouthValue);
                    lastMouthValue = mouthValue;
                }
            }
            
            await Task.Delay(50); // Check every 50ms
        }
        
        servo.Stop();
        lipSyncEngine.Stop();
        
        Console.WriteLine("Diagnostics complete!");
    }

    static async Task RunComboTest()
    {
        Console.WriteLine("Audio + Servo Combination Test");
        Console.WriteLine("==============================");

        var bundlePath = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059";
        var audioPath = Path.Combine(bundlePath, "original.m4a");

        if (!File.Exists(audioPath))
        {
            Console.WriteLine($"Error: Audio file not found at {audioPath}");
            return;
        }

        using var audioPlayer = new AudioPlayer();
        using var servo = new ServoController(0); // Channel 0

        // Set up event handlers
        audioPlayer.PlaybackStarted += (s, e) => Console.WriteLine("🎵 Audio started playing!");
        audioPlayer.PlaybackStopped += (s, e) => Console.WriteLine("🔇 Audio stopped.");

        try
        {
            Console.WriteLine("Setting up audio and servo...");
            await audioPlayer.LoadAudioFileAsync(audioPath);
            
            Console.WriteLine("Testing servo before audio starts...");
            servo.SetCenter(); // Start at center position
            await Task.Delay(2000); // Wait 2 seconds to see initial movement
            
            Console.WriteLine("Servo should be at center now. Starting audio...");
            
            // Start audio
            audioPlayer.Play();
            await Task.Delay(1000); // Give audio time to start
            
            // Move servo in sync with audio for demonstration
            Console.WriteLine("🎭 Performing mouth movements...");
            
            // Simpler, slower movement pattern with more delays
            var movementPattern = new[]
            {
                (0.2, "Slightly open", 3000),
                (0.8, "Wide open", 3000), 
                (0.1, "Nearly closed", 3000),
                (0.6, "Medium open", 3000),
                (0.0, "Fully closed", 3000),
                (0.5, "Half open", 3000)
            };

            foreach (var (position, description, durationMs) in movementPattern)
            {
                Console.WriteLine($"Moving servo to: {description} (position {position})");
                servo.SetPosition(position);
                Console.WriteLine($"Waiting {durationMs}ms...");
                await Task.Delay(durationMs);
            }
            
            // Stop everything
            Console.WriteLine("Demo completed, stopping audio and servo...");
            audioPlayer.Stop();
            Console.WriteLine("Setting servo to center...");
            servo.SetCenter();
            await Task.Delay(2000);
            Console.WriteLine("Stopping servo PWM...");
            servo.Stop();
            
            Console.WriteLine("✅ Audio + Servo combination test completed successfully!");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error: {ex.Message}");
        }
    }

    static async Task RunServoTest()
    {
        Console.WriteLine("Servo Control Test");
        Console.WriteLine("==================");

        // Test multiple channels in case channel 0 has an issue
        var channelsToTest = new[] { 0, 1, 2 };
        
        foreach (var channel in channelsToTest)
        {
            Console.WriteLine($"\n🔧 Testing servo on channel {channel}...");
            
            try
            {
                using var servo = new ServoController(channel);
                
                Console.WriteLine("Starting servo test sequence...");
                
                // Test sequence with wider pulse range for compatibility
                var positions = new[] { 0.0, 0.5, 1.0, 0.5 }; // 0°, 90°, 180°, 90°
                var positionNames = new[] { "0° (500μs)", "90° (1500μs)", "180° (2500μs)", "90° (1500μs)" };
                
                for (int i = 0; i < positions.Length; i++)
                {
                    Console.WriteLine($"\n  Moving to position {i + 1}/4: {positionNames[i]}");
                    servo.SetPosition(positions[i]);
                    
                    // Wait 3 seconds between movements for observation
                    await Task.Delay(3000);
                }
                
                Console.WriteLine($"\n✅ Channel {channel} test completed!");
                servo.Stop();
                await Task.Delay(1000);
                
                // Ask user if they saw movement
                Console.WriteLine($"\n❓ Did you see the servo move on channel {channel}? (Press any key to test next channel or Ctrl+C to exit)");
                Console.ReadKey();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Channel {channel} test failed: {ex.Message}");
            }
        }
        
        Console.WriteLine("\n📋 Troubleshooting Checklist:");
        Console.WriteLine("1. 🔌 Is external 5V power supply connected to the servo HAT?");
        Console.WriteLine("2. 🔋 Power supply should be 5V, 2A or higher");
        Console.WriteLine("3. 🔌 Check servo wiring: Red(+), Black(-), Signal wire to PWM");
        Console.WriteLine("4. 💡 Look for power LED on the servo HAT");
        Console.WriteLine("5. 🔄 Try a different servo or different channel");
        Console.WriteLine("6. 📏 Some servos need 3.3V logic level shifters");
    }

    static async Task RunAudioTest()
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
            
            Console.WriteLine("Starting playback for 10 seconds...");
            audioPlayer.Play();
            
            // Let it play for 10 seconds
            await Task.Delay(10000);
            
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