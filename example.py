import array
import wave
import struct
import argparse
import ctypes

import numpy as np
from pydub import AudioSegment

import sbc


def read_wav_file(filename):
    """Read PCM data from a WAV file."""
    with wave.open(filename, 'rb') as wav_file:
        # Get file properties
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        # Read all frames
        frames = wav_file.readframes(n_frames)
        
        # Convert to array of 16-bit integers
        if sample_width == 2:  # 16-bit
            if n_channels == 1:
                pcm = array.array('h', frames)
            else:
                raise ValueError("Only mono WAV files are supported")
        else:
            raise ValueError(f"Unsupported sample width: {sample_width} bytes")
        
        return pcm, sample_rate, n_channels


def write_wav_file(filename, pcm_bytes, sample_rate, n_channels):
    """Write PCM data to a WAV file."""
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(n_channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)


def mono_ch_codec(input_file, output_file):
    """Encode a WAV file to an SBC file."""
    # Read the WAV file
    pcm_data, sample_rate, n_channels = read_wav_file(input_file)
    
    # Create the encoder
    encoder = sbc.Encoder(
        nsubbands=8,
        nblocks=16,
        frequency=sbc.SBCFreq.FREQ_16K,
        mode=sbc.SBCMode.MONO,
        bitpool=32,
    )
    
    # Get the frame samples
    frame_samples = encoder.get_frame_samples()
    
    # Encode the PCM data frame by frame
    encoded_frames = b''
    for i in range(0, len(pcm_data), frame_samples):
        # Get a frame of PCM data
        frame_bytes = pcm_data[i:i + frame_samples]
        
        # Pad with zeros if needed
        if len(frame_bytes) < frame_samples:
            frame_bytes.extend([0] * (frame_samples - len(frame_bytes)))
        
        # Encode the frame
        encoded_frame = encoder.encode(frame_bytes)
        encoded_frames += encoded_frame

    print(f"Encoded {len(encoded_frames)} frames")
    print(f"Frame size: {encoder.get_frame_size()} bytes")
    print(f"Frame samples: {encoder.get_frame_samples()} samples")
    print(f"Bitrate: {encoder.get_frame_bitrate()} bps")

    # Create a decoder with initial parameters (these will be updated after probing)
    # We'll use some standard values initially
    decoder = sbc.Decoder(
        nsubbands=8,
        nblocks=16,
        frequency=sbc.SBCFreq.FREQ_16K,
        mode=sbc.SBCMode.MONO
    )
    frame_size = decoder.get_frame_size()

    decoded_frames = b''

    # Decode the data frame by frame
    for i in range(frame_size, len(encoded_frames), frame_size):
        # Get a frame of SBC data
        frame_data = encoded_frames[i:i + frame_size]
        
        # Skip incomplete frames
        if len(frame_data) < frame_size:
            break

        # Decode the frame
        decoded_frame = decoder.decode(frame_data)
        decoded_frames += decoded_frame
    
    # Get sample rate and channels from the frame parameters
    sample_rate = decoder.get_sample_rate_hz()

    # Write the decoded PCM to the output file
    write_wav_file(output_file, decoded_frames, sample_rate, n_channels)

    print(f"Decoded {len(encoded_frames)} // {frame_size} = {len(encoded_frames) // frame_size} frames")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Channels: {n_channels}")


def three_ch_codec(input_file, output_file):
    audio_segment = AudioSegment.from_wav(input_file)
    n_channels = audio_segment.channels
    audio = np.array(audio_segment.get_array_of_samples(), dtype=np.float32).reshape(-1, 3)
    audio = audio.astype(np.int16)

    encoder = [sbc.Encoder(
        nsubbands=8,
        nblocks=16,
        frequency=sbc.SBCFreq.FREQ_16K,
        mode=sbc.SBCMode.MONO,
        bitpool=32,
    ) for _ in range(n_channels)]

    decoder = [sbc.Decoder(
        nsubbands=8,
        nblocks=16,
        frequency=sbc.SBCFreq.FREQ_16K,
        mode=sbc.SBCMode.MONO
    ) for _ in range(n_channels)]

    frame_samples = encoder[0].get_frame_samples()
    frame_size = encoder[0].get_frame_size()
    print(f"Frame size: {frame_size} bytes")
    print(f"Frame samples: {frame_samples} samples")

    # pad audio to be divisible by frame_samples
    if audio.shape[0] % frame_samples != 0:
        len_frame = audio.shape[0] % frame_samples
        print(f"Padding {frame_samples - len_frame} samples")
        audio = np.pad(audio, ((0, frame_samples - len_frame), (0, 0)), mode="constant")

    # pad one additional frame to the end of audio
    print(f"Audio shape: {audio.shape}")
    audio = np.pad(audio, ((0, frame_samples), (0, 0)), mode="constant")
    print(f"Audio shape: {audio.shape}")

    # SBC encoding by frame_samples
    encoded = [b'' for _ in range(n_channels)]
    for i in range(n_channels):
        # loop through each frame size in audio.shape[0]
        for j in range(0, audio.shape[0], frame_samples):
            frame = audio[j:j + frame_samples, i]
            encoded[i] += encoder[i].encode(frame.tolist())
        print(f"Encoded {len(encoded[i])} frames.")

    # Write the encoded data to a file
    with open(output_file.replace(".wav", ".sbc"), 'wb') as f:
        for i in range(n_channels):
            f.write(encoded[i])

    # SBC decoding by frame_size
    decoded = [b'' for _ in range(n_channels)]
    for i in range(n_channels):
        # loop through each frame size in mixed.shape[0]
        for j in range(0, len(encoded[i]), frame_size):
            encoded_frame = encoded[i][j:j + frame_size]
            decoded[i] += decoder[i].decode(encoded_frame)

        print(f"Decoded {len(decoded[i])} frames.")

    decoded_np = np.array([np.frombuffer(decoded[i], dtype=np.int16) for i in range(n_channels)]).T
    print(f"Decoded shape: {decoded_np.shape}")
    # remove the first 73 samples (SBC delay) of audio at the beginning
    decoded_np = decoded_np[73:]
    print(f"Decoded shape: {decoded_np.shape}")
    # remove the rest of padded frame of audio at the end
    decoded_np = decoded_np[:-(frame_samples - 73)]
    print(f"Decoded shape: {decoded_np.shape}")

    decoded_audio = AudioSegment(data=decoded_np.tobytes(), sample_width=2, frame_rate=16000, channels=n_channels)
    decoded_audio.export(output_file, format="wav")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input file')
    parser.add_argument('--output', required=True, help='Output file')
    args = parser.parse_args()

    # mono_ch_codec(args.input, args.output)
    three_ch_codec(args.input, args.output)


if __name__ == '__main__':
    main()