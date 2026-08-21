using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace SonicScout;

public sealed record SetupCheckResult(string Name, string State, string Detail);
public sealed record AudioEndpointOption(string Id, string DisplayName);
public sealed record SetupInstallRequest(
    string SelectedOutputId,
    string SelectedOutputName,
    string SetupStyle,
    bool ConfirmOwnership,
    bool ConfirmRoutingApply,
    bool ConfirmDependencyFallback,
    bool UsesVoicemeeter,
    bool UsesWaveLink,
    bool UsesSoundBlaster,
    bool UsesOtherMixer);

public partial class SetupWindow : Window
{
    private const string SonicScoutDirectRouteStyle = "Sonic Scout Direct Route";
    private const string SonicScoutCompatibilityRouteStyle = "Sonic Scout Compatibility Route";

    private readonly Func<Task<IReadOnlyList<AudioEndpointOption>>> discoverOutputs;
    private readonly Func<IProgress<SetupCheckResult>, SetupInstallRequest, Task<IReadOnlyList<SetupCheckResult>>> runChecks;
    private readonly Func<Window, Task> openPostInstallVerification;
    private readonly Dictionary<string, (Ellipse Indicator, TextBlock Heading, TextBlock Detail)> rows = new();
    private readonly List<AudioEndpointOption> discoveredOutputs = new();

    public SetupWindow(
        Func<Task<IReadOnlyList<AudioEndpointOption>>> discoverOutputs,
        Func<IProgress<SetupCheckResult>, SetupInstallRequest, Task<IReadOnlyList<SetupCheckResult>>> runChecks,
        Func<Window, Task> openPostInstallVerification)
    {
        InitializeComponent();
        this.discoverOutputs = discoverOutputs;
        this.runChecks = runChecks;
        this.openPostInstallVerification = openPostInstallVerification;
        Loaded += async (_, _) => await LoadInstallOptionsAsync();
    }

    private async Task LoadInstallOptionsAsync()
    {
        SetInstallerInputEnabled(false);
        ProgressBar.IsIndeterminate = true;
        SummaryText.Text = "Discovering active input/output devices...";
        CheckList.Items.Clear();
        rows.Clear();

        try
        {
            IReadOnlyList<AudioEndpointOption> outputs = await discoverOutputs();
            discoveredOutputs.Clear();
            discoveredOutputs.AddRange(outputs);
            DefaultOutputComboBox.Items.Clear();
            foreach (AudioEndpointOption output in discoveredOutputs)
            {
                DefaultOutputComboBox.Items.Add(output.DisplayName);
            }

            if (discoveredOutputs.Count == 0)
            {
                CheckList.Items.Add(CreateRow(new SetupCheckResult("Device discovery", "UPDATE", "No active output endpoints were detected. Connect your playback device and reopen setup.")));
                SummaryText.Text = "No active output devices found.";
                DoneButton.IsEnabled = true;
                DoneButton.Content = "CLOSE";
                return;
            }

            DefaultOutputComboBox.SelectedIndex = 0;
            SetupStyleComboBox.SelectedIndex = 0;
            OwnershipConsentCheckBox.IsChecked = false;
            RoutingConsentCheckBox.IsChecked = false;
            DependencyConsentCheckBox.IsChecked = false;
            UpdateSetupStyleHint();
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Device discovery", "READY", $"Discovered {discoveredOutputs.Count} active output endpoint(s).")));
            SummaryText.Text = "Select your default output and compatibility flags, then run setup.";
            StepText.Text = "STEP 1 OF 4  |  CHOOSE YOUR OUTPUT, ROUTE STYLE, AND COMPATIBILITY";
            SetInstallerInputEnabled(true);
            DoneButton.IsEnabled = true;
            DoneButton.Content = "CLOSE";
        }
        catch (COMException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Device discovery", "ERROR", $"Windows Core Audio failed to enumerate endpoints: {exception.Message}")));
            SummaryText.Text = "Device discovery failed.";
            DoneButton.IsEnabled = true;
            DoneButton.Content = "CLOSE";
        }
        catch (UnauthorizedAccessException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Device discovery", "ERROR", $"Windows denied access to device metadata: {exception.Message}")));
            SummaryText.Text = "Device discovery failed.";
            DoneButton.IsEnabled = true;
            DoneButton.Content = "CLOSE";
        }
        catch (IOException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Device discovery", "ERROR", $"A file or driver IO operation failed while loading devices: {exception.Message}")));
            SummaryText.Text = "Device discovery failed.";
            DoneButton.IsEnabled = true;
            DoneButton.Content = "CLOSE";
        }
        finally
        {
            ProgressBar.IsIndeterminate = false;
            ProgressBar.Value = 0;
        }
    }

    private SetupInstallRequest BuildInstallRequest()
    {
        if (DefaultOutputComboBox.SelectedIndex < 0 || DefaultOutputComboBox.SelectedIndex >= discoveredOutputs.Count)
        {
            throw new InvalidOperationException("Select an active output endpoint before running setup.");
        }

        AudioEndpointOption selectedOutput = discoveredOutputs[DefaultOutputComboBox.SelectedIndex];
        return new SetupInstallRequest(
            selectedOutput.Id,
            selectedOutput.DisplayName,
            GetSelectedSetupStyle(),
            OwnershipConsentCheckBox.IsChecked == true,
            RoutingConsentCheckBox.IsChecked == true,
            DependencyConsentCheckBox.IsChecked == true,
            VoicemeeterCheckBox.IsChecked == true,
            WaveLinkCheckBox.IsChecked == true,
            SoundBlasterCheckBox.IsChecked == true,
            OtherMixerCheckBox.IsChecked == true);
    }

    private string GetSelectedSetupStyle()
    {
        if (SetupStyleComboBox.SelectedItem is ComboBoxItem selectedStyle &&
            selectedStyle.Content is string setupStyle &&
            !string.IsNullOrWhiteSpace(setupStyle))
        {
            return setupStyle;
        }

        return SonicScoutDirectRouteStyle;
    }

    private void UpdateSetupStyleHint()
    {
        string setupStyle = GetSelectedSetupStyle();
        bool compatibilityRouteStyle = string.Equals(setupStyle, SonicScoutCompatibilityRouteStyle, StringComparison.OrdinalIgnoreCase);
        SetupStyleHintText.Text = compatibilityRouteStyle
            ? "Sonic Scout compatibility route keeps mixer-safe routing active to avoid third-party chain conflicts."
            : "Sonic Scout direct route prioritizes low-latency virtual routing.";
    }

    private void SetInstallerInputEnabled(bool enabled)
    {
        DefaultOutputComboBox.IsEnabled = enabled;
        SetupStyleComboBox.IsEnabled = enabled;
        OwnershipConsentCheckBox.IsEnabled = enabled;
        RoutingConsentCheckBox.IsEnabled = enabled;
        DependencyConsentCheckBox.IsEnabled = enabled;
        VoicemeeterCheckBox.IsEnabled = enabled;
        WaveLinkCheckBox.IsEnabled = enabled;
        SoundBlasterCheckBox.IsEnabled = enabled;
        OtherMixerCheckBox.IsEnabled = enabled;
        UpdateRunButtonState(enabled);
    }

    private bool HasRequiredConsents()
    {
        return OwnershipConsentCheckBox.IsChecked == true &&
               RoutingConsentCheckBox.IsChecked == true &&
               DependencyConsentCheckBox.IsChecked == true;
    }

    private void UpdateRunButtonState(bool setupInputsEnabled)
    {
        BeginSetupButton.IsEnabled = setupInputsEnabled && discoveredOutputs.Count > 0;
        BeginSetupButton.Content = HasRequiredConsents()
            ? "RUN INSTALL SETUP"
            : "CONFIRM 3 CHECKBOXES ABOVE";
    }

    private void SetupStyleComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        UpdateSetupStyleHint();
    }

    private void ConsentCheckBox_Changed(object sender, RoutedEventArgs e)
    {
        UpdateRunButtonState(DefaultOutputComboBox.IsEnabled);
    }

    private async void BeginSetupButton_Click(object sender, RoutedEventArgs e)
    {
        await RunChecksAsync();
    }

    private async Task RunChecksAsync()
    {
        if (DefaultOutputComboBox.SelectedIndex < 0 || DefaultOutputComboBox.SelectedIndex >= discoveredOutputs.Count)
        {
            SummaryText.Text = "Select a default output endpoint before running setup.";
            return;
        }
        if (!HasRequiredConsents())
        {
            SummaryText.Text = "Confirm ownership, routing apply permission, and dependency acknowledgement before running setup.";
            return;
        }

        SetupInstallRequest request = BuildInstallRequest();
        Progress<SetupCheckResult> progress = new(result =>
        {
            if (rows.TryGetValue(result.Name, out var row))
            {
                row.Indicator.Fill = (System.Windows.Media.Brush)FindResource(GetStateBrush(result.State));
                row.Heading.Text = $"{result.State}  {result.Name}";
                row.Detail.Text = result.Detail;
            }
            else
            {
                CheckList.Items.Add(CreateRow(result));
                CheckList.ScrollIntoView(CheckList.Items[^1]);
            }
            SummaryText.Text = result.Detail;
        });

        SetInstallerInputEnabled(false);
        StepText.Text = "STEP 2 OF 4  |  CHECKING AND INSTALLING AUDIO COMPONENTS";
        DoneButton.IsEnabled = false;
        BeginSetupButton.IsEnabled = false;
        BeginSetupButton.Content = "RUNNING INSTALL SETUP...";
        ProgressBar.IsIndeterminate = true;
        ProgressBar.Value = 0;
        CheckList.Items.Clear();
        rows.Clear();

        try
        {
            IReadOnlyList<SetupCheckResult> results = await runChecks(progress, request);
            int problems = results.Count(result => result.State is "UPDATE" or "ERROR");
            SummaryText.Text = problems == 0
                ? "Installation routing is configured and ready."
                : $"{problems} item(s) need attention. Review the results below.";
            DoneButton.Content = problems == 0 ? "DONE" : "CLOSE AND REVIEW";
            VerifySettingsButton.IsEnabled = true;
            StepText.Text = problems == 0
                ? "STEP 3 OF 4  |  AUDIO STACK READY - VERIFY WINDOWS SETTINGS"
                : "STEP 3 OF 4  |  REVIEW ITEMS NEEDING ATTENTION";
        }
        catch (InvalidOperationException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Setup", "ERROR", exception.Message)));
            SummaryText.Text = "Setup stopped with an error.";
            DoneButton.Content = "CLOSE";
        }
        catch (UnauthorizedAccessException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Permissions", "ERROR", exception.Message)));
            SummaryText.Text = "Setup stopped due to permissions.";
            DoneButton.Content = "CLOSE";
        }
        catch (IOException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("I/O", "ERROR", exception.Message)));
            SummaryText.Text = "Setup stopped due to an IO error.";
            DoneButton.Content = "CLOSE";
        }
        catch (COMException exception)
        {
            CheckList.Items.Add(CreateRow(new SetupCheckResult("Core Audio", "ERROR", exception.Message)));
            SummaryText.Text = "Setup stopped due to a Windows audio error.";
            DoneButton.Content = "CLOSE";
        }
        finally
        {
            ProgressBar.IsIndeterminate = false;
            ProgressBar.Value = 1;
            DoneButton.IsEnabled = true;
            BeginSetupButton.Content = "RUN INSTALL SETUP";
            SetInstallerInputEnabled(discoveredOutputs.Count > 0);
        }
    }

    private Border CreateRow(SetupCheckResult result)
    {
        StackPanel content = new() { Margin = new Thickness(0, 2, 0, 2) };
        Grid rowGrid = new();
        rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(14) });
        rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        Ellipse indicator = new() { Width = 9, Height = 9, Fill = (System.Windows.Media.Brush)FindResource(GetStateBrush(result.State)), VerticalAlignment = VerticalAlignment.Top, Margin = new Thickness(0, 5, 0, 0) };
        TextBlock heading = new() { Text = $"{result.State}  {result.Name}", Foreground = (System.Windows.Media.Brush)FindResource(GetStateBrush(result.State)), FontSize = 12, FontWeight = FontWeights.Bold };
        TextBlock detail = new() { Text = result.Detail, Foreground = (System.Windows.Media.Brush)FindResource("PopupTextBrush"), Opacity = 0.82, FontSize = 11, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 3, 0, 0) };
        StackPanel text = new();
        text.Children.Add(heading);
        text.Children.Add(detail);
        rowGrid.Children.Add(indicator);
        Grid.SetColumn(text, 1);
        rowGrid.Children.Add(text);
        content.Children.Add(rowGrid);
        rows[result.Name] = (indicator, heading, detail);
        return new Border { Padding = new Thickness(10, 7, 10, 7), Margin = new Thickness(0, 0, 0, 5), Background = System.Windows.Media.Brushes.Transparent, Child = content };
    }

    private static string GetStateBrush(string state) => state switch
    {
        "READY" or "FIXED" => "SetupReadyBrush",
        "RUNNING" => "SetupRunningBrush",
        "UPDATE" => "SetupUpdateBrush",
        "ERROR" => "SetupErrorBrush",
        _ => "PopupTextBrush"
    };

    private void CloseButton_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }

    private async void VerifySettingsButton_Click(object sender, RoutedEventArgs e)
    {
        StepText.Text = "STEP 4 OF 4  |  VERIFY THE SETTINGS THAT WINDOWS CANNOT REPORT";
        await openPostInstallVerification(this);
    }

    private void Header_MouseLeftButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        if (e.ChangedButton == System.Windows.Input.MouseButton.Left)
        {
            DragMove();
        }
    }
}
