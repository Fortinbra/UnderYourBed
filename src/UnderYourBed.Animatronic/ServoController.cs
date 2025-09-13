using System.Device.I2c;
using Iot.Device.Pwm;

namespace UnderYourBed.Animatronic.Hardware;

public class ServoController : IDisposable
{
    private readonly Pca9685 _pca9685;
    private readonly double _minPulseWidth;
    private readonly double _maxPulseWidth;
    private readonly int _frequency;
    private readonly int _channel;
    private bool _isDisposed;

    /// <summary>
    /// Creates a new servo controller using the Adafruit 16-Channel PWM/Servo HAT
    /// </summary>
    /// <param name="channel">Servo channel on the HAT (0-15)</param>
    /// <param name="i2cAddress">I2C address of the PCA9685 (default 0x40)</param>
    /// <param name="minPulseWidth">Minimum pulse width in microseconds (typically 500-1000)</param>
    /// <param name="maxPulseWidth">Maximum pulse width in microseconds (typically 2000-2500)</param>
    /// <param name="frequency">PWM frequency in Hz (typically 50 for servos)</param>
    public ServoController(int channel, int i2cAddress = 0x40, double minPulseWidth = 500, double maxPulseWidth = 2500, int frequency = 50)
    {
        if (channel < 0 || channel > 15)
            throw new ArgumentOutOfRangeException(nameof(channel), "Channel must be between 0 and 15");

        _channel = channel;
        _minPulseWidth = minPulseWidth;
        _maxPulseWidth = maxPulseWidth;
        _frequency = frequency;

        try
        {
            // Create I2C device
            var i2cSettings = new I2cConnectionSettings(1, i2cAddress); // Bus 1, address 0x40
            var i2cDevice = I2cDevice.Create(i2cSettings);
            
            // Initialize PCA9685
            _pca9685 = new Pca9685(i2cDevice);
            _pca9685.PwmFrequency = frequency;
            
            Console.WriteLine($"Servo controller initialized on channel {channel} (I2C address 0x{i2cAddress:X2})");
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"Failed to initialize servo controller: {ex.Message}", ex);
        }
    }

    /// <summary>
    /// Move servo to a specific angle
    /// </summary>
    /// <param name="angleDegrees">Angle in degrees (0-180)</param>
    public void SetAngle(double angleDegrees)
    {
        if (_isDisposed)
            throw new ObjectDisposedException(nameof(ServoController));

        // Clamp angle to valid range
        angleDegrees = Math.Max(0, Math.Min(180, angleDegrees));

        // Convert angle to pulse width
        var pulseWidth = _minPulseWidth + (angleDegrees / 180.0) * (_maxPulseWidth - _minPulseWidth);
        
        // Convert pulse width to duty cycle for PCA9685
        var periodMicroseconds = 1_000_000.0 / _frequency; // Period in microseconds
        var dutyCycle = pulseWidth / periodMicroseconds;

        // Set the PWM duty cycle for this channel
        _pca9685.SetDutyCycle(_channel, dutyCycle);
        
        Console.WriteLine($"Servo channel {_channel} set to {angleDegrees:F1}° (pulse: {pulseWidth:F0}μs, duty: {dutyCycle:P2})");
    }

    /// <summary>
    /// Move servo to a position between 0.0 (0°) and 1.0 (180°)
    /// </summary>
    /// <param name="position">Position from 0.0 to 1.0</param>
    public void SetPosition(double position)
    {
        position = Math.Max(0.0, Math.Min(1.0, position));
        SetAngle(position * 180.0);
    }

    /// <summary>
    /// Move servo to center position (90°)
    /// </summary>
    public void SetCenter()
    {
        SetAngle(90);
    }

    /// <summary>
    /// Stop PWM signal to servo (servo will become unpowered)
    /// </summary>
    public void Stop()
    {
        if (!_isDisposed)
        {
            _pca9685.SetDutyCycle(_channel, 0);
            Console.WriteLine($"Servo channel {_channel} PWM stopped");
        }
    }

    /// <summary>
    /// Resume PWM signal to servo at last position
    /// </summary>
    public void Start()
    {
        if (!_isDisposed)
        {
            // Just set center position when starting
            SetCenter();
            Console.WriteLine($"Servo channel {_channel} PWM started");
        }
    }

    public void Dispose()
    {
        if (!_isDisposed)
        {
            Stop();
            _pca9685?.Dispose();
            _isDisposed = true;
            Console.WriteLine($"Servo controller channel {_channel} disposed");
        }
    }
}