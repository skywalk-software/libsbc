import array
import ctypes
import enum
import glob
import os
import platform
import sys
from pathlib import Path

from ctypes import c_bool, c_byte, c_int, c_uint, c_size_t, c_void_p, c_int16
from ctypes.util import find_library


class SBCFreq(enum.IntEnum):
    """SBC sampling frequency"""
    FREQ_16K = 0  # 16 kHz
    FREQ_32K = 1  # 32 kHz
    FREQ_44K1 = 2  # 44.1 kHz
    FREQ_48K = 3  # 48 kHz


class SBCMode(enum.IntEnum):
    """SBC channel mode"""
    MONO = 0  # Mono
    DUAL_CHANNEL = 1  # Dual channel
    STEREO = 2  # Stereo
    JOINT_STEREO = 3  # Joint stereo


class SBCBAM(enum.IntEnum):
    """SBC bit allocation method"""
    LOUDNESS = 0  # Loudness
    SNR = 1  # Signal-to-noise ratio


class _Base:
    """Base class for SBC encoder and decoder"""

    def __init__(self, nsubbands, nblocks, frequency, mode=SBCMode.MONO, bam=SBCBAM.LOUDNESS, **kwargs):
        """
        Initialize the SBC base object with common parameters.
        
        Args:
            nsubbands: Number of subbands (4 or 8)
            nblocks: Number of blocks (4, 8, 12, or 16)
            frequency: Sampling frequency (one of the SBCFreq values)
            mode: Channel mode (one of the SBCMode values)
            bam: Bit allocation method (one of the SBCBAM values)
            
        Keyword args:
            bitpool: Bit pool value for encoding (default is 32)
            libpath: Path to the SBC library (if not in standard locations)
        """
        self.nsubbands = nsubbands
        self.nblocks = nblocks
        self.freq = frequency
        self.mode = mode
        self.bam = bam
        self.bitpool = 32  # Default bitpool value
        self.msbc = False
        
        libpath = None
        
        for k in kwargs.keys():
            if k == 'bitpool':
                self.bitpool = int(kwargs[k])
            elif k == 'libpath':
                libpath = kwargs[k]
            elif k == 'msbc':
                self.msbc = bool(kwargs[k])
            else:
                raise ValueError("Invalid keyword argument: " + k)
        
        # Validate parameters
        if nsubbands not in [4, 8]:
            raise ValueError("Invalid number of subbands, must be 4 or 8")
        
        if nblocks not in [4, 8, 12, 16]:
            raise ValueError("Invalid number of blocks, must be 4, 8, 12, or 16")
            
        if not isinstance(frequency, SBCFreq):
            raise ValueError("Invalid frequency value")
            
        if not isinstance(mode, SBCMode):
            raise ValueError("Invalid mode value")
            
        if not isinstance(bam, SBCBAM):
            raise ValueError("Invalid bit allocation method")
        
        # Load the SBC library
        self.lib = self._load_library(libpath)
        
        # Get C standard library for memory allocation
        libc = ctypes.cdll.LoadLibrary(find_library("c"))
        
        self.malloc = libc.malloc
        self.malloc.argtypes = [c_size_t]
        self.malloc.restype = c_void_p
        
        self.free = libc.free
        self.free.argtypes = [c_void_p]
        
        # Define SBC frame struct
        class SBCFrame(ctypes.Structure):
            _fields_ = [
                ("msbc", c_bool),
                ("freq", c_int),
                ("mode", c_int),
                ("bam", c_int),
                ("nblocks", c_int),
                ("nsubbands", c_int),
                ("bitpool", c_int)
            ]
        
        self.SBCFrame = SBCFrame
        self.frame = SBCFrame(
            msbc=self.msbc,
            freq=self.freq,
            mode=self.mode,
            bam=self.bam,
            nblocks=self.nblocks,
            nsubbands=self.nsubbands,
            bitpool=self.bitpool
        )
        
        # Set up function prototypes
        self.lib.sbc_get_freq_hz.argtypes = [c_int]
        self.lib.sbc_get_freq_hz.restype = c_int
        
        self.lib.sbc_get_frame_size.argtypes = [ctypes.POINTER(SBCFrame)]
        self.lib.sbc_get_frame_size.restype = c_uint
        
        self.lib.sbc_get_frame_bitrate.argtypes = [ctypes.POINTER(SBCFrame)]
        self.lib.sbc_get_frame_bitrate.restype = c_uint
    
    def _load_library(self, libpath=None):
        """
        Load the SBC library, prioritizing:
        1. User-provided explicit path
        2. Library packaged with this module
        3. System-installed library
        """
        if libpath is not None:
            return ctypes.cdll.LoadLibrary(libpath)
        
        # Try to load from package directory first
        package_dir = Path(__file__).parent.absolute()
        system = platform.system()
        
        if system == 'Linux':
            lib_name = 'libsbc.so'
        elif system == 'Darwin':
            lib_name = 'libsbc.dylib'
        elif system == 'Windows':
            lib_name = 'libsbc.dll'
        else:
            lib_name = 'libsbc.so'  # Default to Linux naming
        
        packaged_lib = package_dir / lib_name
        if packaged_lib.exists():
            try:
                return ctypes.cdll.LoadLibrary(str(packaged_lib))
            except OSError:
                pass  # Fall back to other methods
        
        # Try to find in system paths
        system_lib = find_library("sbc")
        if system_lib:
            return ctypes.cdll.LoadLibrary(system_lib)
        
        # Final fallback: search common directories
        common_dirs = [
            '/usr/lib',
            '/usr/local/lib',
            '/opt/local/lib',
        ]
        
        for d in common_dirs:
            pattern = os.path.join(d, f'*{lib_name}*')
            matches = glob.glob(pattern)
            if matches:
                return ctypes.cdll.LoadLibrary(matches[0])
        
        # If we got here, we couldn't find the library
        raise Exception(f"SBC library ({lib_name}) not found. Please install it or specify the path using libpath.")
    
    def get_frame_size(self):
        """
        Returns the size of an SBC frame in bytes.
        """
        ret = self.lib.sbc_get_frame_size(ctypes.byref(self.frame))
        if ret == 0:
            raise ValueError("Bad parameters")
        return ret
    
    def get_frame_bitrate(self):
        """
        Returns the bitrate of the SBC frame in bits per second.
        """
        ret = self.lib.sbc_get_frame_bitrate(ctypes.byref(self.frame))
        if ret == 0:
            raise ValueError("Bad parameters")
        return ret
    
    def get_sample_rate_hz(self):
        """
        Returns the sample rate in Hz based on the frequency enum.
        """
        ret = self.lib.sbc_get_freq_hz(self.freq)
        if ret <= 0:
            raise ValueError("Bad parameters")
        return ret
    
    def get_frame_samples(self):
        """
        Returns the number of PCM samples in an SBC frame.
        """
        return self.nblocks * self.nsubbands


class Encoder(_Base):
    """
    SBC Encoder wrapper
    
    Parameters:
        nsubbands: Number of subbands (4 or 8)
        nblocks: Number of blocks (4, 8, 12, or 16)
        frequency: Sampling frequency (one of the SBCFreq values)
        mode: Channel mode (one of the SBCMode values)
        bam: Bit allocation method (one of the SBCBAM values)
        
    Keyword parameters:
        bitpool: Bit pool value for encoding (default is 32)
        msbc: Whether to use mSBC mode (default is False)
        libpath: Path to the SBC library (if not in standard locations)
    """
    
    def __init__(self, nsubbands, nblocks, frequency, mode=SBCMode.MONO, bam=SBCBAM.LOUDNESS, **kwargs):
        super().__init__(nsubbands, nblocks, frequency, mode, bam, **kwargs)
        
        # Define SBC struct
        class SBC(ctypes.Structure):
            _fields_ = [
                ("nchannels", c_int),
                ("nblocks", c_int),
                ("nsubbands", c_int),
                ("_estates", c_byte * 700) 
            ]
        
        self.SBC = SBC
        
        # Set up encoder function prototypes
        self.lib.sbc_reset.argtypes = [ctypes.POINTER(SBC)]
        
        self.lib.sbc_encode.argtypes = [
            ctypes.POINTER(SBC),
            ctypes.POINTER(c_int16),  # pcml
            c_int,                     # pitchl
            ctypes.POINTER(c_int16),  # pcmr
            c_int,                     # pitchr
            ctypes.POINTER(self.SBCFrame),
            c_void_p,                  # data
            c_uint                     # size
        ]
        self.lib.sbc_encode.restype = c_int
        
        # Initialize the SBC context
        nchannels = 1
        if self.mode != SBCMode.MONO:
            nchannels = 2
            
        self.sbc = SBC(
            nchannels=nchannels,
            nblocks=self.nblocks,
            nsubbands=self.nsubbands
        )
        
        self.lib.sbc_reset(ctypes.byref(self.sbc))
    
    def encode(self, pcm):
        """
        Encode PCM samples to SBC frame.
        
        Args:
            pcm: Input PCM data as a list or array of 16-bit integers.
                 For stereo, samples should be interleaved [L, R, L, R, ...].
        
        Returns:
            Encoded SBC frame as bytes.
        """
        frame_samples = self.get_frame_samples()
        
        # Determine if we have mono or stereo
        is_stereo = (self.mode != SBCMode.MONO)
        
        # Convert input to ctypes array
        pcm_buffer = (c_int16 * len(pcm))(*pcm)
        
        # Allocate buffer for encoded data
        frame_size = self.get_frame_size()
        data_buffer = (c_byte * frame_size)()
        
        # Set up PCM pointers for left and right channels
        if is_stereo:
            # For stereo, we pass pcml, pitchl=2, pcmr=pcml+1, pitchr=2
            pcml = pcm_buffer
            pitchl = 2
            pcmr = ctypes.cast(ctypes.addressof(pcm_buffer) + ctypes.sizeof(c_int16), 
                              ctypes.POINTER(c_int16))
            pitchr = 2
        else:
            # For mono, we pass pcml, pitchl=1, pcmr=NULL, pitchr=0
            pcml = pcm_buffer
            pitchl = 1
            pcmr = None
            pitchr = 0
        
        # Call the encode function
        ret = self.lib.sbc_encode(
            ctypes.byref(self.sbc),
            pcml, pitchl,
            pcmr, pitchr,
            ctypes.byref(self.frame),
            data_buffer, frame_size
        )
        
        if ret < 0:
            raise ValueError("SBC encoding failed")
        
        return bytes(data_buffer)


class Decoder(_Base):
    """
    SBC Decoder wrapper
    
    Parameters:
        nsubbands: Number of subbands (4 or 8)
        nblocks: Number of blocks (4, 8, 12, or 16)
        frequency: Sampling frequency (one of the SBCFreq values)
        mode: Channel mode (one of the SBCMode values)
        bam: Bit allocation method (one of the SBCBAM values)
        
    Keyword parameters:
        msbc: Whether to use mSBC mode (default is False)
        libpath: Path to the SBC library (if not in standard locations)
    """
    
    def __init__(self, nsubbands, nblocks, frequency, mode=SBCMode.MONO, bam=SBCBAM.LOUDNESS, **kwargs):
        super().__init__(nsubbands, nblocks, frequency, mode, bam, **kwargs)
        
        # Define SBC struct
        class SBC(ctypes.Structure):
            _fields_ = [
                ("nchannels", c_int),
                ("nblocks", c_int),
                ("nsubbands", c_int),
                ("_dstates", c_byte * 700)  
            ]
        
        self.SBC = SBC
        
        # Set up decoder function prototypes
        self.lib.sbc_reset.argtypes = [ctypes.POINTER(SBC)]
        
        self.lib.sbc_probe.argtypes = [c_void_p, ctypes.POINTER(self.SBCFrame)]
        self.lib.sbc_probe.restype = c_int
        
        self.lib.sbc_decode.argtypes = [
            ctypes.POINTER(SBC),
            c_void_p,                  # data
            c_uint,                    # size
            ctypes.POINTER(self.SBCFrame),
            ctypes.POINTER(c_int16),  # pcml
            c_int,                     # pitchl
            ctypes.POINTER(c_int16),  # pcmr
            c_int                      # pitchr
        ]
        self.lib.sbc_decode.restype = c_int
        
        # Initialize the SBC context
        nchannels = 1
        if self.mode != SBCMode.MONO:
            nchannels = 2
            
        self.sbc = SBC(
            nchannels=nchannels,
            nblocks=self.nblocks,
            nsubbands=self.nsubbands
        )
        
        self.lib.sbc_reset(ctypes.byref(self.sbc))
    
    def decode(self, data):
        """
        Decode SBC frame to PCM samples.
        
        Args:
            data: Input SBC frame data as bytes or bytearray.
        
        Returns:
            Decoded PCM samples as array.array('h') (16-bit integers).
            For stereo, samples are interleaved [L, R, L, R, ...].
        """
        # Check input data
        if len(data) < 4:  # SBC_HEADER_SIZE
            raise ValueError("Input data too small")
        
        # Probe the data to verify it's a valid SBC frame
        data_buffer = (c_byte * len(data)).from_buffer_copy(data)
        temp_frame = self.SBCFrame()
        
        ret = self.lib.sbc_probe(data_buffer, ctypes.byref(temp_frame))
        if ret < 0:
            raise ValueError("Invalid SBC frame")
        
        # Update our frame parameters based on what we found in the data
        self.frame = temp_frame
        
        # Determine if we have mono or stereo
        is_stereo = (self.frame.mode != SBCMode.MONO)
        
        # Calculate number of PCM samples to output
        frame_samples = self.frame.nblocks * self.frame.nsubbands
        total_samples = frame_samples * (2 if is_stereo else 1)
        
        # Allocate buffer for decoded PCM
        pcm_buffer = (c_int16 * total_samples)()
        
        # Set up PCM pointers for left and right channels
        if is_stereo:
            # For stereo, we pass pcml, pitchl=2, pcmr=pcml+1, pitchr=2
            pcml = pcm_buffer
            pitchl = 2
            pcmr = ctypes.cast(ctypes.addressof(pcm_buffer) + ctypes.sizeof(c_int16), 
                              ctypes.POINTER(c_int16))
            pitchr = 2
        else:
            # For mono, we pass pcml, pitchl=1, pcmr=NULL, pitchr=0
            pcml = pcm_buffer
            pitchl = 1
            pcmr = None
            pitchr = 0
        
        # Call the decode function
        ret = self.lib.sbc_decode(
            ctypes.byref(self.sbc),
            data_buffer, len(data),
            ctypes.byref(self.frame),
            pcml, pitchl,
            pcmr, pitchr
        )
        
        if ret < 0:
            raise ValueError("SBC decoding failed")
        
        # Convert to Python array
        return bytes(pcm_buffer)


# Convenience function to get a sample rate in Hz from a frequency enum
def get_sample_rate_hz(freq):
    """Get the sample rate in Hz from an SBCFreq enum value."""
    sample_rates = {
        SBCFreq.FREQ_16K: 16000,
        SBCFreq.FREQ_32K: 32000,
        SBCFreq.FREQ_44K1: 44100,
        SBCFreq.FREQ_48K: 48000
    }
    return sample_rates.get(freq, 0) 
