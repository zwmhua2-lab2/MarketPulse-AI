import socket

import uvicorn
from uvicorn.protocols.http.h11_impl import H11Protocol

from marketpulse.api.product.market_candles import _connection
from marketpulse.config import get_settings


def _local_config(app, listener):
    """Only this entry supplies socket objects, never a header/scope boolean proof."""
    class LocalHTTP(H11Protocol):
        def connection_made(self, transport):
            super().connection_made(transport)
            original = self.app

            async def connected(scope, receive, send):
                token = _connection.set((listener, transport.get_extra_info("socket")))
                try:
                    await original(scope, receive, send)
                finally:
                    _connection.reset(token)

            self.app = connected

    return uvicorn.Config(app, http=LocalHTTP, proxy_headers=False, ws="none")


if __name__ == "__main__":
    settings = get_settings()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((settings.host, settings.port))
        uvicorn.Server(_local_config("marketpulse.api.app:app", listener)).run(sockets=[listener])
