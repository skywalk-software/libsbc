# Subband Codec (SBC)

The SBC codec is the mandotory codec for Bluetooth audio over A2DP Profile

The technical specification of the codec is covered in Appendix B of [_Advanced Audio Distribution_](https://www.bluetooth.org/docman/handlers/downloaddoc.ashx?doc_id=457083)

mSBC extension is covered by Appendix A of [_Hands-Free Profile_](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=489628)

## Overview

The directory layout is as follows :
- include:      Library interface
- src:          Source files
- tools:        Standalone encoder/decoder tools
- build:        Building outputs
- bin:          Compilation output

## How to build

The default toolchain used is GCC. Invoke `make` to build the library.

```sh
$ make -j
```

Compiled library `libsbc.a` will be found in `bin` directory.

#### Cross compilation

The cc, as, ld and ar can be selected with respective Makefile variables `CC`,
`AS`, `LD` and `AR`. The `AS` and `LD` selections are optionnal, and fallback
to `CC` selection when not defined.

```sh
$ make -j CC=path_to_toolchain/bin/toolchain-prefix-gcc CFLAGS="..."
```

Compiled library will be found in `bin` directory.

#### Enabling assembly

Assembly code is available for armv7-em architecture. Enabling assembly code
is done with the `ARCH` Makefile variable. Following example enable assembly
optimization for target CPU ARM Cortex M4 :

```sh
$ make -j CC=path_to_arm_toolchain/bin/toolchain-prefix-gcc \
    CFLAGS="-mcpu=cortex-m4 -mthumb" ARCH="arm-v7em"
```
## Tools

Tools can be all compiled, while involking `make` as follows :

```sh
$ make tools
```

The standalone encoder `esbc` take a `wave` file as input and encode it
according given parameter. The standalone decoder `dsbc` do the inverse
operation.

Refer to `esbc -h` or `dsbc -h` for options.

Note that `esbc` output bitstream to standard output when output file is
omitted. On the other side `dsbc` read from standard input when input output
file are omitted.
In such way you can easly test encoding / decoding loop with :

```sh
$ ./esbc <in.wav> -b <bitpool> | ./dsbc > <out.wav>
```

Adding Linux `aplay` tools, you are able to instant hear the result :

```sh
$ ./esbc <in.wav> -b <bitpool> | ./dsbc | aplay
```

# Python SBC Wrapper

A Python wrapper for the SBC (Sub-band Codec) library, similar to the liblc3 wrapper. This allows Python applications to encode and decode audio using the SBC codec.

## Features

- Encode mono or stereo audio to SBC frames
- Decode SBC frames to PCM audio
- Support for different sampling rates (16kHz, 32kHz, 44.1kHz, 48kHz)
- Configure encoding parameters (subbands, blocks, bit allocation method, bitpool)
- Support for mSBC (optional)

## Requirements

- Python 3.7+
- SBC library (e.g., libsbc.so or libsbc.dylib)

## Installation

The SBC library needs to be installed on your system. The wrapper will look for it in standard library locations.

The Python package is located in the `python` directory and can be installed using pip:

```bash
# Install directly from the repository
pip install .

# For development
pip install -e .
```

## Usage

### Basic Usage

```python
from sbc import SBCFreq, SBCMode, SBCBAM, Encoder, Decoder

# Create an encoder for 16kHz mono audio
encoder = Encoder(
    nsubbands=8,
    nblocks=16,
    frequency=SBCFreq.FREQ_16K,
    mode=SBCMode.MONO,
    bitpool=32
)

# Encode PCM samples (16-bit integers)
pcm_samples = [0, 100, 200, ...]  # Your PCM data here
encoded_frame = encoder.encode(pcm_samples)

# Create a decoder
decoder = Decoder(
    nsubbands=8,
    nblocks=16,
    frequency=SBCFreq.FREQ_16K,
    mode=SBCMode.MONO
)

# Decode SBC frame back to PCM
decoded_samples = decoder.decode(encoded_frame)
```

### Encoding a WAV file

See the `example.py` script for a complete example of encoding and decoding WAV files.

```bash
# Run the example script
python example.py --input input.wav --output output.wav
```

## API Reference

### SBC Frequency Enum (`SBCFreq`)

- `FREQ_16K` (0): 16 kHz
- `FREQ_32K` (1): 32 kHz
- `FREQ_44K1` (2): 44.1 kHz
- `FREQ_48K` (3): 48 kHz

### SBC Channel Mode Enum (`SBCMode`)

- `MONO` (0): Mono mode
- `DUAL_CHANNEL` (1): Dual channel mode
- `STEREO` (2): Stereo mode
- `JOINT_STEREO` (3): Joint stereo mode

### SBC Bit Allocation Method Enum (`SBCBAM`)

- `LOUDNESS` (0): Loudness allocation
- `SNR` (1): Signal-to-noise ratio allocation

### Encoder Class

```python
encoder = sbc.Encoder(
    nsubbands,          # Number of subbands (4 or 8)
    nblocks,            # Number of blocks (4, 8, 12, or 16)
    frequency,          # Sampling frequency (SBCFreq enum)
    mode=SBCMode.MONO,  # Channel mode (SBCMode enum)
    bam=SBCBAM.LOUDNESS, # Bit allocation method (SBCBAM enum)
    bitpool=32,         # Bitpool value (controls quality)
    msbc=False          # mSBC mode (for Bluetooth HFP)
)

# Encode PCM samples to SBC frame
encoded_frame = encoder.encode(pcm_samples)

# Get info about the frame
frame_size = encoder.get_frame_size()       # Size in bytes
bitrate = encoder.get_frame_bitrate()       # Bitrate in bits per second
sample_rate = encoder.get_sample_rate_hz()  # Sample rate in Hz
frame_samples = encoder.get_frame_samples() # Number of samples per frame
```

### Decoder Class

```python
decoder = sbc.Decoder(
    nsubbands,          # Number of subbands (4 or 8)
    nblocks,            # Number of blocks (4, 8, 12, or 16)
    frequency,          # Sampling frequency (SBCFreq enum)
    mode=SBCMode.MONO,  # Channel mode (SBCMode enum)
    bam=SBCBAM.LOUDNESS, # Bit allocation method (SBCBAM enum)
    msbc=False          # mSBC mode (for Bluetooth HFP)
)

# Decode SBC frame to PCM samples
decoded_samples = decoder.decode(encoded_frame)

# Get info about the frame
frame_size = decoder.get_frame_size()       # Size in bytes
bitrate = decoder.get_frame_bitrate()       # Bitrate in bits per second
sample_rate = decoder.get_sample_rate_hz()  # Sample rate in Hz
frame_samples = decoder.get_frame_samples() # Number of samples per frame
```
