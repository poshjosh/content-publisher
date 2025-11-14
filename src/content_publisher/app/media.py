import struct
import os
from pathlib import Path


class Media:
    @staticmethod
    def get_video_size_bytes(video_file_path):
        return Path(video_file_path).stat().st_size

    @staticmethod
    def get_video_duration_seconds(filename, fallback):
        """
        Get video duration in seconds.
        Supports MP4, MOV, and AVI formats.
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")

        duration = Media._read_mp4_duration(filename)
        return fallback if duration is None else duration

    @staticmethod
    def _read_mp4_duration(filename):
        """
        Read duration of MP4/MOV video files.
        Returns duration in seconds.
        """
        try:
            with open(filename, 'rb') as f:
                # Find 'moov' box (movie container)
                result = Media.find_box(f, b'moov')
                if not result:
                    return None

                moov_size, moov_start = result
                moov_end = moov_start + moov_size - 8

                # Search for 'mvhd' inside moov box
                result = Media.find_box(f, b'mvhd', moov_end - f.tell())
                if not result:
                    return None

                # Read mvhd box data
                version = struct.unpack('B', f.read(1))[0]
                f.read(3)  # flags

                if version == 1:
                    f.read(16)  # creation and modification time (64-bit each)
                    timescale = struct.unpack('>I', f.read(4))[0]
                    duration = struct.unpack('>Q', f.read(8))[0]
                else:
                    f.read(8)  # creation and modification time (32-bit each)
                    timescale = struct.unpack('>I', f.read(4))[0]
                    duration = struct.unpack('>I', f.read(4))[0]

                if timescale == 0:
                    return None

                return duration / timescale

        except Exception as e:
            print(f"Error reading MP4: {e}")
            return None

    @staticmethod
    def find_box(f, target_type, max_search=None):
        """Search for a specific box type in the file."""
        start_pos = f.tell()

        while True:
            if max_search and (f.tell() - start_pos) >= max_search:
                return None

            size, box_type, data_start = Media._read_box_header(f)

            if size is None:
                return None

            if box_type == target_type:
                return size, data_start

            # Skip to next box
            if size == 0:  # Box extends to end of file
                break

            next_pos = data_start + size - 8
            if size == 1:
                next_pos -= 8  # Account for extended size

            f.seek(next_pos)

        return None

    @staticmethod
    def _read_box_header(f):
        """Read an MP4 box header (size and type)."""
        data = f.read(8)
        if len(data) < 8:
            return None, None, None

        size = struct.unpack('>I', data[:4])[0]
        box_type = data[4:8]

        # Handle extended size (size == 1 means 64-bit size follows)
        if size == 1:
            size = struct.unpack('>Q', f.read(8))[0]

        return size, box_type, f.tell()