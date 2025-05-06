#!/usr/bin/env python3
"""
A simple test script to verify SBC package functionality.
"""

import sys

try:
    from sbc import SBCFreq, SBCMode, SBCBAM, Encoder, Decoder, get_sample_rate_hz
except ImportError:
    print("Error: Unable to import SBC package. Make sure it's installed with 'pip install .'")
    sys.exit(1)

def test_imports():
    """Test that all imports are working correctly"""
    print("SBC package imported successfully!")
    print(f"SBCFreq.FREQ_44K1 = {SBCFreq.FREQ_44K1}")
    print(f"SBCMode.STEREO = {SBCMode.STEREO}")
    print(f"SBCBAM.LOUDNESS = {SBCBAM.LOUDNESS}")
    print(f"Sample rate for 44.1kHz: {get_sample_rate_hz(SBCFreq.FREQ_44K1)} Hz")
    print("Import test passed!")

if __name__ == "__main__":
    print("Testing SBC package...")
    test_imports()
    print("All tests passed!") 