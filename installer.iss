[Setup]
AppName=Automatizador de Boletas Electronicas
AppVersion=1.0
AppPublisher=Programasound
DefaultDirName={autopf}\Automatizador de Boletas
DefaultGroupName=Automatizador de Boletas
OutputDir=installer_output
OutputBaseFilename=Instalador_AutomatizadorBoletas
SetupIconFile=SRC\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"

[Files]
Source: "dist\Automatizador de Boletas.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTRUCCIONES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "ModeloBoletasAMasiva.xlsx"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Automatizador de Boletas Electronicas"; Filename: "{app}\Automatizador de Boletas.exe"
Name: "{group}\Desinstalar"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Automatizador de Boletas Electronicas"; Filename: "{app}\Automatizador de Boletas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Automatizador de Boletas.exe"; Description: "Abrir la aplicacion"; Flags: nowait postinstall skipifsilent
