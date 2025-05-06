# SBC Python Bindings

Python bindings for the SBC (SubBand Codec) library, used primarily for Bluetooth audio.

## Installation

### Requirements

- Python 3.7 or newer
- C compiler (gcc, clang, etc.)
- Make

The package will automatically build the native SBC library during installation, so you don't need to install it separately.

### Installing the Package

```bash
# Install directly from the repository
pip install .

# For development
pip install -e .
```

The installation process will:
1. Build the native SBC library using make
2. Create the appropriate shared library (.so on Linux, .dylib on macOS, .dll on Windows)
3. Package the shared library with the Python bindings

### Manual Installation

If the automatic build fails, you can build the native library manually:

```bash
# First build the library
make
# On macOS, you might need to create a dynamic library
make dynamic  # Creates libsbc.dylib from libsbc.a

# Then install the Python package
pip install .
```

## Usage

Here's a quick example of how to use the SBC encoder and decoder:

```python
from sbc import SBCFreq, SBCMode, SBCBAM, Encoder, Decoder

# Create an encoder
encoder = Encoder(
    nsubbands=8,
    nblocks=16,
    frequency=SBCFreq.FREQ_44K1,
    mode=SBCMode.STEREO,
    bitpool=32
)

# Encode PCM data
pcm_data = [...]  # Your 16-bit PCM samples
encoded_data = encoder.encode(pcm_data)

# Create a decoder with the same parameters
decoder = Decoder(
    nsubbands=8,
    nblocks=16,
    frequency=SBCFreq.FREQ_44K1,
    mode=SBCMode.STEREO
)

# Decode the SBC data
decoded_data = decoder.decode(encoded_data)
```

## API Reference

### Enums

- `SBCFreq`: Sampling frequency enumerations
  - `FREQ_16K`: 16 kHz
  - `FREQ_32K`: 32 kHz
  - `FREQ_44K1`: 44.1 kHz
  - `FREQ_48K`: 48 kHz

- `SBCMode`: Channel mode enumerations
  - `MONO`: Mono channel
  - `DUAL_CHANNEL`: Dual channel
  - `STEREO`: Stereo mode
  - `JOINT_STEREO`: Joint stereo mode

- `SBCBAM`: Bit allocation method enumerations
  - `LOUDNESS`: Loudness
  - `SNR`: Signal-to-noise ratio

### Classes

- `Encoder`: SBC encoder class
- `Decoder`: SBC decoder class

### Utility Functions

- `get_sample_rate_hz(freq)`: Get the sample rate in Hz from an SBCFreq enum value

## License

This project is licensed under the MIT License - see the LICENSE file for details. 