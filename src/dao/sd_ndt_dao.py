import logging

import aiohttp

from dao.base import BaseSessionDAO

logger = logging.getLogger(__name__)


class ControlnetClientDAO(BaseSessionDAO):
    def __init__(self, app):
        super().__init__(app)
        self._uri = "/face_based_generation"
        self._auth = aiohttp.BasicAuth(app["config"]["stable_diffusion"]["service_name"],
                                       app["config"]["stable_diffusion"]["service_id"],
                                       encoding="utf-8")
        self._session: aiohttp.ClientSession = self.session_manager.SD

    def _build_body_for_generation(self, prompt: str, negative_prompt: str):
        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "batch_size": 1,
            "sampler_name": "DPM++ 2M SDE Karras",
            "steps": 35,
            "cfg_scale": 7,
            "width": 870,
            "height": 1152,
            "seed": -1,
            "subseed": -1
        }

    async def generate(self, b64_photo: str, prompt: str, negative_prompt: str) -> dict:
        try:
            async with self._session.post(self._uri,
                                          json={
                                              "params": self._build_body_for_generation(prompt, negative_prompt),
                                              "b64_photo_image": b64_photo
                                          },
                                          raise_for_status=True,
                                          auth=self._auth
                                          ) as resp:
                return await resp.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Error in request: {e.status} - {e.message}")
            raise e
