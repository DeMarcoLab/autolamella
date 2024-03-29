import os
import sys
import win32com.client
from autolamella.config import DESKTOP_SHORTCUT_PATH
# Get the user's desktop folder
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')

# Specify the target file (e.g., a script or program you want to create a shortcut for)
target_file = os.path.join(DESKTOP_SHORTCUT_PATH, "ui.bat") # Replace with your program's path

# Create a shortcut name
shortcut_name = 'AutoLamella.lnk'

# Create a shortcut on the desktop
shell = win32com.client.Dispatch("WScript.Shell")
shortcut = shell.CreateShortCut(os.path.join(desktop, shortcut_name))
shortcut.TargetPath = target_file
shortcut.save()

print(f"Shortcut to '{target_file}' created on the desktop as '{shortcut_name}'")