using NAudio.CoreAudioApi;
using NAudio.Wave;

namespace SonicScout.ScoutPass;

internal static class Program
{
    private static int Main(string[] args)
    {
        ScoutPassOptions options;
        try
        {
            options = ScoutPassOptions.Parse(args);
        }
        catch (ArgumentException exception)
        {
            Console.Error.WriteLine(exception.Message);
            ScoutPassOptions.PrintUsage();
            return 2;
        }

        if (options.ShowHelp)
        {
            ScoutPassOptions.PrintUsage();
            return 0;
        }

        using MMDeviceEnumerator enumerator = new();
        MMDevice input = DeviceResolver.ResolveInput(enumerator, options.InputId, options.InputName);
        MMDevice output = DeviceResolver.ResolveOutput(enumerator, options.OutputId, options.OutputName);
        using ScoutPassEngine scoutPass = new(input, output, options.BufferMilliseconds, options.InputGainDb, options.OutputGainDb);

        Console.CancelKeyPress += (_, eventArgs) =>
        {
            eventArgs.Cancel = true;
            scoutPass.Stop();
        };

        scoutPass.Start();
        Console.WriteLine($"ScoutPass running: {input.FriendlyName} -> {output.FriendlyName}");
        Console.WriteLine($"Format: {scoutPass.Format.SampleRate} Hz, {scoutPass.Format.Channels} channel(s), {scoutPass.Format.BitsPerSample}-bit");
        Console.WriteLine("Press Ctrl+C to stop.");

        while (scoutPass.IsRunning)
        {
            Thread.Sleep(1000);
            Console.WriteLine($"Packets: {scoutPass.PacketsReceived}, buffer drops: {scoutPass.BufferDrops}, buffered: {scoutPass.BufferedMilliseconds} ms");
        }

        return scoutPass.LastError is null ? 0 : 1;
    }
}

internal sealed class ScoutPassOptions
{
    public string? InputId { get; private set; }
    public string? InputName { get; private set; }
    public string? OutputId { get; private set; }
    public string? OutputName { get; private set; }
    public int BufferMilliseconds { get; private set; } = 100;
    public double InputGainDb { get; private set; }
    public double OutputGainDb { get; private set; }
    public bool ShowHelp { get; private set; }

    public static ScoutPassOptions Parse(string[] args)
    {
        ScoutPassOptions options = new();
        for (int index = 0; index < args.Length; index++)
        {
            string argument = args[index];
            if (argument is "--help" or "-h")
            {
                options.ShowHelp = true;
                continue;
            }

            string value = ReadValue(args, ref index, argument);
            switch (argument.ToLowerInvariant())
            {
                case "--input-id":
                    options.InputId = value;
                    break;
                case "--input-name":
                    options.InputName = value;
                    break;
                case "--output-id":
                    options.OutputId = value;
                    break;
                case "--output-name":
                    options.OutputName = value;
                    break;
                case "--buffer-ms":
                    if (!int.TryParse(value, out int bufferMilliseconds) || bufferMilliseconds is < 20 or > 500)
                    {
                        throw new ArgumentException("--buffer-ms must be an integer from 20 to 500.");
                    }
                    options.BufferMilliseconds = bufferMilliseconds;
                    break;
                case "--input-gain-db":
                    options.InputGainDb = ParseGain(value, argument);
                    break;
                case "--output-gain-db":
                    options.OutputGainDb = ParseGain(value, argument);
                    break;
                default:
                    throw new ArgumentException($"Unknown ScoutPass option: {argument}");
            }
        }

        return options;
    }

    public static void PrintUsage()
    {
        Console.WriteLine("Sonic Scout ScoutPass");
        Console.WriteLine("  --input-id <id>       Virtual render endpoint ID");
        Console.WriteLine("  --input-name <name>   Virtual render endpoint name fragment");
        Console.WriteLine("  --output-id <id>      Physical render endpoint ID");
        Console.WriteLine("  --output-name <name>  Physical render endpoint name fragment");
        Console.WriteLine("  --buffer-ms <20..500> Shared-mode buffer target");
        Console.WriteLine("  --input-gain-db <-12..12> Input boost/cut");
        Console.WriteLine("  --output-gain-db <-12..12> Output boost/cut");
    }

    private static string ReadValue(string[] args, ref int index, string argument)
    {
        if (index + 1 >= args.Length || args[index + 1].StartsWith("--", StringComparison.Ordinal))
        {
            throw new ArgumentException($"Missing value for {argument}.");
        }

        return args[++index];
    }

    private static double ParseGain(string value, string argument)
    {
        if (!double.TryParse(value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double gain) || gain is < -12 or > 12)
        {
            throw new ArgumentException($"{argument} must be between -12 and 12 dB.");
        }

        return gain;
    }
}

internal static class DeviceResolver
{
    private static readonly string[] VirtualEndpointHints =
    [
        "Sonic Scout", "VB-Audio", "VB-Cable", "Virtual Cable", "CABLE Input", "Hi-Fi Cable"
    ];

    public static MMDevice ResolveInput(MMDeviceEnumerator enumerator, string? id, string? name)
    {
        if (!string.IsNullOrWhiteSpace(id))
        {
            return enumerator.GetDevice(id);
        }

        MMDeviceCollection devices = enumerator.EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active);
        MMDevice? match = devices.FirstOrDefault(device =>
            !string.IsNullOrWhiteSpace(name) && device.FriendlyName.Contains(name, StringComparison.OrdinalIgnoreCase));
        match ??= enumerator.EnumerateAudioEndPoints(DataFlow.Render, DeviceState.Active).FirstOrDefault(device =>
            !string.IsNullOrWhiteSpace(name) && device.FriendlyName.Contains(name, StringComparison.OrdinalIgnoreCase));
        match ??= devices.FirstOrDefault(device => VirtualEndpointHints.Any(hint =>
            device.FriendlyName.Contains(hint, StringComparison.OrdinalIgnoreCase)));
        match ??= enumerator.EnumerateAudioEndPoints(DataFlow.Render, DeviceState.Active).FirstOrDefault(device => VirtualEndpointHints.Any(hint =>
            device.FriendlyName.Contains(hint, StringComparison.OrdinalIgnoreCase)));
        return match ?? throw new InvalidOperationException("No Sonic Scout virtual render endpoint was found. Install or select a virtual audio driver.");
    }

    public static MMDevice ResolveOutput(MMDeviceEnumerator enumerator, string? id, string? name)
    {
        if (!string.IsNullOrWhiteSpace(id))
        {
            return enumerator.GetDevice(id);
        }

        MMDeviceCollection devices = enumerator.EnumerateAudioEndPoints(DataFlow.Render, DeviceState.Active);
        MMDevice? match = devices.FirstOrDefault(device =>
            !string.IsNullOrWhiteSpace(name) && device.FriendlyName.Contains(name, StringComparison.OrdinalIgnoreCase));
        match ??= enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
        return match;
    }
}

internal sealed class ScoutPassEngine : IDisposable
{
    private readonly MMDevice inputDevice;
    private readonly MMDevice outputDevice;
    private readonly int bufferMilliseconds;
    private readonly float gainMultiplier;
    private readonly object stateLock = new();
    private IWaveIn? capture;
    private WasapiOut? output;
    private BufferedWaveProvider? buffer;
    private MediaFoundationResampler? resampler;
    private long packetsReceived;
    private long bufferDrops;
    private bool stopped;

    public ScoutPassEngine(MMDevice inputDevice, MMDevice outputDevice, int bufferMilliseconds, double inputGainDb, double outputGainDb)
    {
        this.inputDevice = inputDevice;
        this.outputDevice = outputDevice;
        this.bufferMilliseconds = bufferMilliseconds;
        gainMultiplier = (float)Math.Pow(10, (inputGainDb + outputGainDb) / 20.0);
    }

    public WaveFormat Format => capture?.WaveFormat ?? throw new InvalidOperationException("ScoutPass has not started.");
    public bool IsRunning { get; private set; }
    public Exception? LastError { get; private set; }
    public long PacketsReceived => Interlocked.Read(ref packetsReceived);
    public long BufferDrops => Interlocked.Read(ref bufferDrops);
    public int BufferedMilliseconds => buffer is null ? 0 : (int)buffer.BufferedDuration.TotalMilliseconds;

    public void Start()
    {
        lock (stateLock)
        {
            if (IsRunning)
            {
                return;
            }

            capture = inputDevice.DataFlow == DataFlow.Capture
                ? new WasapiCapture(inputDevice)
                : new WasapiLoopbackCapture(inputDevice);
            buffer = new BufferedWaveProvider(capture.WaveFormat)
            {
                BufferDuration = TimeSpan.FromMilliseconds(Math.Max(bufferMilliseconds * 4, 200)),
                DiscardOnBufferOverflow = true,
                ReadFully = true
            };
            WaveFormat outputFormat = outputDevice.AudioClient.MixFormat;
            IWaveProvider playbackProvider = buffer;
            if (!AreCompatibleFormats(capture.WaveFormat, outputFormat))
            {
                resampler = new MediaFoundationResampler(buffer, outputFormat)
                {
                    ResamplerQuality = 60
                };
                playbackProvider = resampler;
            }
            output = new WasapiOut(outputDevice, AudioClientShareMode.Shared, true, bufferMilliseconds);
            output.Init(playbackProvider);
            capture.DataAvailable += CaptureOnDataAvailable;
            capture.RecordingStopped += CaptureOnRecordingStopped;
            output.PlaybackStopped += OutputOnPlaybackStopped;

            // Capture must deliver at least one packet before Play() starts the WASAPI render
            // thread; NAudio's WasapiOut treats an empty first read as end-of-stream and silently
            // exits without ever calling AudioClient.Start(), leaving PlaybackState stuck at Playing.
            capture.StartRecording();
            SpinWait.SpinUntil(() => buffer.BufferedBytes > 0, TimeSpan.FromSeconds(2));
            output.Play();
            stopped = false;
            IsRunning = true;
        }
    }

    public void Stop()
    {
        lock (stateLock)
        {
            if (stopped)
            {
                return;
            }

            stopped = true;
            IsRunning = false;
            try
            {
                capture?.StopRecording();
            }
            catch (Exception exception)
            {
                LastError ??= exception;
            }

            try
            {
                output?.Stop();
            }
            catch (Exception exception)
            {
                LastError ??= exception;
            }
        }
    }

    public void Dispose()
    {
        Stop();
        capture?.Dispose();
        resampler?.Dispose();
        output?.Dispose();
        inputDevice.Dispose();
        outputDevice.Dispose();
    }

    private void CaptureOnDataAvailable(object? sender, WaveInEventArgs eventArgs)
    {
        if (buffer is null || eventArgs.BytesRecorded == 0)
        {
            return;
        }

        ApplyGain(eventArgs.Buffer, eventArgs.BytesRecorded);
        int before = buffer.BufferedBytes;
        buffer.AddSamples(eventArgs.Buffer, 0, eventArgs.BytesRecorded);
        if (buffer.BufferedBytes == before && eventArgs.BytesRecorded > 0)
        {
            Interlocked.Increment(ref bufferDrops);
        }
        Interlocked.Increment(ref packetsReceived);
    }

    private static bool AreCompatibleFormats(WaveFormat input, WaveFormat output)
    {
        return input.Encoding == output.Encoding &&
               input.SampleRate == output.SampleRate &&
               input.Channels == output.Channels &&
               input.BitsPerSample == output.BitsPerSample;
    }

    private void ApplyGain(byte[] samples, int bytesRecorded)
    {
        if (Math.Abs(gainMultiplier - 1f) < 0.0001f)
        {
            return;
        }

        if (Format.Encoding == WaveFormatEncoding.IeeeFloat && Format.BitsPerSample == 32)
        {
            for (int offset = 0; offset + 4 <= bytesRecorded; offset += 4)
            {
                float sample = BitConverter.ToSingle(samples, offset);
                float adjusted = Math.Clamp(sample * gainMultiplier, -1f, 1f);
                BitConverter.TryWriteBytes(samples.AsSpan(offset, 4), adjusted);
            }
        }
        else if (Format.Encoding == WaveFormatEncoding.Pcm && Format.BitsPerSample == 16)
        {
            for (int offset = 0; offset + 2 <= bytesRecorded; offset += 2)
            {
                short sample = BitConverter.ToInt16(samples, offset);
                short adjusted = (short)Math.Clamp(sample * gainMultiplier, short.MinValue, short.MaxValue);
                BitConverter.TryWriteBytes(samples.AsSpan(offset, 2), adjusted);
            }
        }
    }

    private void CaptureOnRecordingStopped(object? sender, StoppedEventArgs eventArgs)
    {
        if (eventArgs.Exception is not null)
        {
            LastError = eventArgs.Exception;
        }
        IsRunning = false;
    }

    private void OutputOnPlaybackStopped(object? sender, StoppedEventArgs eventArgs)
    {
        if (eventArgs.Exception is not null)
        {
            LastError = eventArgs.Exception;
        }
        IsRunning = false;
    }
}
