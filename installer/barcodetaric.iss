; Inno Setup script — per-user εγκατάσταση (χωρίς admin/UAC), ελληνικός wizard.
#define AppName "BarcodeTaric"
#define AppVersion "0.1.0"
#define AppPublisher "scanmydata"
#define AppExe "BarcodeTaric.exe"

[Setup]
AppId={{B7A1C2D3-4E5F-6789-ABCD-BARCODETARIC01}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename={#AppName}-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "el"; MessagesFile: "compiler:Default.isl"

[Messages]
el.WelcomeLabel2=Θα εγκατασταθεί το [name/ver] στον υπολογιστή σας.%n%nΣυνιστάται να κλείσετε άλλες εφαρμογές πριν συνεχίσετε.

[Tasks]
Name: "desktopicon"; Description: "Δημιουργία εικονιδίου στην επιφάνεια εργασίας"; GroupDescription: "Πρόσθετα:"
Name: "autostart"; Description: "Εκκίνηση με τα Windows"; GroupDescription: "Πρόσθετα:"; Flags: unchecked

[Files]
Source: "..\dist\BarcodeTaric\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\scanmydata\BarcodeTaric"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\scanmydata\BarcodeTaric"; ValueType: string; ValueName: "DataDir"; ValueData: "{userappdata}\BarcodeTaric"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BarcodeTaric"; ValueData: """{app}\{#AppExe}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Εκκίνηση {#AppName}"; Flags: nowait postinstall skipifsilent
