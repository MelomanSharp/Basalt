[Setup]
AppName=Basalt
AppVersion=1.0
AppPublisher=MelomanSharp
DefaultDirName={autopf}\Basalt
DefaultGroupName=Basalt
OutputDir=Output
OutputBaseFilename=Basalt_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\Basalt.exe

[Files]
Source: "dist\Basalt.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Basalt"; Filename: "{app}\Basalt.exe"
Name: "{group}\Uninstall Basalt"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Basalt"; Filename: "{app}\Basalt.exe"

[Run]
Filename: "{app}\Basalt.exe"; Description: "Запустить Basalt"; Flags: nowait postinstall skipifsilent