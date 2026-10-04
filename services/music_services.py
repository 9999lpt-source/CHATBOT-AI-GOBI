import asyncio
import av
import time
from yt_dlp import YoutubeDL

class MusicStreamService:
    def __init__(self, sample_rate: int = 16000, layout: str = 'mono', format_pcm: str = 's16'):
        self.sample_rate = sample_rate
        self.layout = layout
        self.format_pcm = format_pcm

    async def stream_audio_pcm(self, search_query: str, chunk_size: int = 2048):
        """
        Tìm kiếm video YouTube, stream & decode bằng PyAV thành PCM raw byte.
        """
        print(f"🔍 Đang tìm kiếm: '{search_query}'...")

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'default_search': 'scsearch1:',
            'noplaylist': True,
        }

        loop = asyncio.get_running_loop()
        def extract():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                return info.get('url'), info.get('title', 'Unknown')

        audio_url, title = await loop.run_in_executor(None, extract)
        if not audio_url:
            print("❌ Không tìm thấy stream audio!")
            return

        print(f"🎵 Đang phát: {title}")

        # Tính toán thời gian thực của 1 chunk (2048 bytes / (16000 * 2) = 0.064s)
        # Giảm nhẹ xuống 0.055s để server luôn chạy nhanh hơn loa một tí, tránh cạn buffer ESP32
        chunk_duration = (chunk_size / (self.sample_rate * 2)) * 0.85 

        try:
            container = av.open(audio_url)
            audio_stream = next(s for s in container.streams if s.type == 'audio')

            resampler = av.AudioResampler(
                format=self.format_pcm,
                layout=self.layout,
                rate=self.sample_rate
            )

            pcm_buffer = bytearray()

            for packet in container.demux(audio_stream):
                for frame in packet.decode():
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        raw_pcm = r_frame.to_ndarray().tobytes()
                        pcm_buffer.extend(raw_pcm)

                        while len(pcm_buffer) >= chunk_size:
                            chunk = bytes(pcm_buffer[:chunk_size])
                            del pcm_buffer[:chunk_size]
                            
                            yield chunk
                            
                            # CỰC KỲ QUAN TRỌNG: Nhường Event Loop + Điều tiết tốc độ
                            await asyncio.sleep(chunk_duration)

            # Flush bộ đệm resampler còn sót lại
            rest_frames = resampler.resample(None)
            if rest_frames:
                for r_frame in rest_frames:
                    pcm_buffer.extend(r_frame.to_ndarray().tobytes())

            while len(pcm_buffer) >= chunk_size:
                yield bytes(pcm_buffer[:chunk_size])
                del pcm_buffer[:chunk_size]
                await asyncio.sleep(chunk_duration)

            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [AUDIO ERROR]: Lỗi stream/decode audio: {e}")