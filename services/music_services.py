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
            # Chọn audio tốt nhất, nếu không có thì lấy video/audio bất kỳ rồi giải mã âm thanh
            'format': 'bestaudio/best',
            'quiet': True,
            'default_search': 'ytsearch1:',
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'source_address': '0.0.0.0',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }

        loop = asyncio.get_running_loop()
        def extract():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if not info:
                    return None, None
                
                # Nếu là danh sách kết quả tìm kiếm (ytsearch1:)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                
                if not info:
                    return None, None

                return info.get('url'), info.get('title', 'Unknown')

        audio_url, title = await loop.run_in_executor(None, extract)
        
        # Bắt chặt trường hợp không lấy được URL stream
        if not audio_url:
            print("❌ Không tìm thấy stream audio hoặc video không hỗ trợ!")
            return

        print(f"🎵 Đang phát: {title}")

        try:
            container = av.open(audio_url)
            audio_stream = next((s for s in container.streams if s.type == 'audio'), None)

            if not audio_stream:
                print("❌ Không tìm thấy luồng audio trong stream!")
                return

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
                            yield bytes(pcm_buffer[:chunk_size])
                            del pcm_buffer[:chunk_size]

            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [AUDIO ERROR]: Lỗi stream/decode audio: {e}")