import os
import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.install import install


class BuildLibraryCommand(build_py):
    """Build the SBC library before building the Python package."""
    
    def run(self):
        # Build the native library
        print("Building native SBC library...")
        subprocess.check_call(['make', '-j'])
        
        # Copy the library to the package directory
        lib_path = os.path.join('bin', 'libsbc.so')
        if sys.platform == 'darwin':
            lib_path = os.path.join('bin', 'libsbc.dylib')
            # On macOS, if the file is libsbc.a, we need to build as dynamic library
            if not os.path.exists(lib_path) and os.path.exists(os.path.join('bin', 'libsbc.a')):
                print("Converting static library to dynamic library for macOS...")
                subprocess.check_call(['make', 'dynamic'])
        elif sys.platform == 'win32':
            lib_path = os.path.join('bin', 'libsbc.dll')
        
        # Ensure target directory exists
        os.makedirs(os.path.join('python', 'sbc'), exist_ok=True)
        
        # Copy library if it exists
        if os.path.exists(lib_path):
            dest_path = os.path.join('python', 'sbc', os.path.basename(lib_path))
            print(f"Copying {lib_path} to {dest_path}")
            subprocess.check_call(['cp', lib_path, dest_path])
        else:
            print(f"Warning: Could not find library at {lib_path}")
            print("Available files in bin directory:")
            if os.path.exists('bin'):
                print(subprocess.check_output(['ls', '-la', 'bin']).decode())
            else:
                print("bin directory does not exist")
        
        # Continue with normal build_py
        build_py.run(self)


# Run the standard setup function
setup(
    cmdclass={
        'build_py': BuildLibraryCommand,
    }
) 