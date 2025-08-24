import warnings

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module=r"^binance\.ws\.websocket_api"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module=r"^websockets\.legacy"
)
