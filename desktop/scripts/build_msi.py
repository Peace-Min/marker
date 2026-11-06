"""Generate WiX input from the staged, self-contained Windows bundle."""
import argparse
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
import uuid

NS = "http://wixtoolset.org/schemas/v4/wxs"
ET.register_namespace("", NS)


def element(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{NS}}}{tag}", {key: str(value) for key, value in attrs.items()})


def identifier(prefix, path):
    return prefix + hashlib.sha256(str(path).encode()).hexdigest()[:25]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("wxs", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    root = ET.Element(f"{{{NS}}}Wix")
    package = element(root, "Package", Name="Marker Desktop Offline", Manufacturer="Marker Desktop",
                      Version="0.1.0", UpgradeCode="89FC673A-8C9D-4AE5-86CA-E25F75BFC498", Scope="perUser", Compressed="yes")
    element(package, "MajorUpgrade", DowngradeErrorMessage="A newer version of Marker Desktop is installed.")
    element(package, "MediaTemplate", EmbedCab="yes", CompressionLevel="mszip", MaximumUncompressedMediaSize="1400")
    local = element(package, "StandardDirectory", Id="LocalAppDataFolder")
    programs = element(local, "Directory", Id="ProgramsFolder", Name="Programs")
    install = element(programs, "Directory", Id="INSTALLFOLDER", Name="MarkerDesktop")
    directories = {Path("."): install}
    feature = element(package, "Feature", Id="MainFeature", Title="Marker Desktop", Level="1")
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(bundle)
        current = Path(".")
        for part in relative.parts[:-1]:
            parent = current
            current /= part
            if current not in directories:
                directories[current] = element(directories[parent], "Directory", Id=identifier("D", current), Name=part)
        component_id = identifier("C", relative)
        guid = str(uuid.uuid5(uuid.UUID("89fc673a-8c9d-4ae5-86ca-e25f75bfc498"), str(relative).replace("\\", "/")))
        component = element(directories[current], "Component", Id=component_id, Guid=guid, Bitness="always64")
        element(component, "File", Id=identifier("F", relative), Source=path, Name=path.name)
        element(component, "RegistryValue", Root="HKCU", Key="Software\\MarkerDesktop\\Files", Name=component_id, Type="integer", Value="1", KeyPath="yes")
        element(feature, "ComponentRef", Id=component_id)
    menu = element(package, "StandardDirectory", Id="ProgramMenuFolder")
    menu_dir = element(menu, "Directory", Id="MarkerMenu", Name="Marker Desktop")
    shortcut = element(menu_dir, "Component", Id="MenuShortcut", Guid="*", Bitness="always64")
    element(shortcut, "Shortcut", Id="AppShortcut", Name="Marker Desktop", Target="[INSTALLFOLDER]Marker.Desktop.exe", WorkingDirectory="INSTALLFOLDER")
    element(shortcut, "RemoveFolder", Id="RemoveMenu", On="uninstall")
    for relative, directory in directories.items():
        element(shortcut, "RemoveFolder", Id=identifier("R", relative), Directory=directory.attrib["Id"], On="uninstall")
    element(shortcut, "RegistryValue", Root="HKCU", Key="Software\\MarkerDesktop", Name="Installed", Type="integer", Value="1", KeyPath="yes")
    element(feature, "ComponentRef", Id="MenuShortcut")
    desktop = element(package, "StandardDirectory", Id="DesktopFolder")
    shortcut = element(desktop, "Component", Id="DesktopShortcut", Guid="*", Bitness="always64")
    element(shortcut, "Shortcut", Id="DesktopAppShortcut", Name="Marker Desktop Offline", Target="[INSTALLFOLDER]Marker.Desktop.exe", WorkingDirectory="INSTALLFOLDER")
    element(shortcut, "RegistryValue", Root="HKCU", Key="Software\\MarkerDesktop", Name="DesktopShortcut", Type="integer", Value="1", KeyPath="yes")
    element(feature, "ComponentRef", Id="DesktopShortcut")
    ET.indent(root)
    ET.ElementTree(root).write(args.wxs, encoding="utf-8", xml_declaration=True)
    print("WiX input generated", args.wxs)


if __name__ == "__main__":
    main()
