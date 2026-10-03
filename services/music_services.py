import asyncio
import av
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
            'default_search': 'ytsearch1:',
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/19.29.37 (Linux; U; Android 11; gts6lvw) gzip',
            }
        }

        # Chạy yt-dlp trong executor để tránh block event loop của asyncio
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

        try:
            # Mở stream HTTP trực tiếp bằng PyAV container
            container = av.open(audio_url)
            audio_stream = next(s for s in container.streams if s.type == 'audio')

            # Bộ chuyển đổi sample rate / channel / format
            resampler = av.AudioResampler(
                format=self.format_pcm,
                layout=self.layout,
                rate=self.sample_rate
            )

            pcm_buffer = bytearray()

            # Demux & decode từng packet từ stream YouTube
            for packet in container.demux(audio_stream):
                for frame in packet.decode():
                    # Resample frame về đúng chuẩn mong muốn (16000Hz, Mono, s16)
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        raw_pcm = r_frame.to_ndarray().tobytes()
                        pcm_buffer.extend(raw_pcm)

                        # Yield từng chunk cố định dung lượng
                        while len(pcm_buffer) >= chunk_size:
                            yield bytes(pcm_buffer[:chunk_size])
                            del pcm_buffer[:chunk_size]

            # Xử lý phần dư còn lại trong buffer
            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [AUDIO ERROR]: Lỗi stream/decode audio: {e}")