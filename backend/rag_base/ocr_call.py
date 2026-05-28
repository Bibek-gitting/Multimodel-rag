import asyncio
from typing import Dict, List, Optional, cast
import httpx

class OcrCall:
    def __init__(self):
        self.SEM = asyncio.Semaphore(3)

    async def get_response_from_ocr(self, images: List) -> list[Optional[Dict[str, str]]]:
        async def send_image(client, img: Dict):
            async with self.SEM:
                for attempt in range(3):
                    try:
                        response = await client.post(
                            "https://nonworking-photoactinic-giuseppe.ngrok-free.dev/ocr",
                            files={"file": ("image.jpg", img["data"])},
                            data={"page": img.get("page",1), "figureno": img.get("figureno",1), "visual_type": img.get("visual_type","general")},
                        )
                        # response = { "ocr_text": "Kolkata is capital of West Bengal. Bengali is the official language of 
                        # the state and the people of the state are known for their hospitality and rich cultural heritage.",
                        # "caption": "Coverpage of a book", "page": img.get("page",1), "figureno": img.get("figureno",1)}
                        print(f"OCR response {response} status for page {img.get('page')}, figure {img.get('figureno')}")
                        if response:
                            return cast(Dict[str, str], response)
                        else:
                            return response
                    except Exception as e:
                        if attempt < 2:
                            await asyncio.sleep(1)
                        else:
                            print(f"OCR failed for page {img.get('page')}: {e}")
                            return None

        async with httpx.AsyncClient(timeout=60.0) as client:
            tasks = [send_image(client, img) for img in images]
            results = await asyncio.gather(*tasks)
            return results #list[{ocr_text,caption,page,figureno},...]
            

