"""
Daytona sandbox runner - manages sandbox lifecycle and execution
"""
import time
from typing import Optional, Dict

from daytona import Daytona


# Cache the Daytona client and sandbox across Streamlit reruns
_daytona_client: Optional[Daytona] = None
_sandbox = None
_sandbox_ready = False


def get_daytona_client(api_key: Optional[str] = None) -> Daytona:
    """Get or create Daytona client"""
    global _daytona_client
    if _daytona_client is None:
        if api_key:
            _daytona_client = Daytona(api_key=api_key)
        else:
            _daytona_client = Daytona()  # reads DAYTONA_API_KEY from env
    return _daytona_client


def get_or_create_sandbox(api_key: Optional[str] = None) -> object:
    """
    Creates a sandbox once and reuses it across runs.
    """
    global _sandbox
    if _sandbox is None:
        daytona = get_daytona_client(api_key)
        _sandbox = daytona.create()
    return _sandbox


def reset_sandbox(api_key: Optional[str] = None):
    """
    Deletes the current sandbox so a fresh one can be created.
    """
    global _sandbox, _sandbox_ready
    if _sandbox is not None:
        daytona = get_daytona_client(api_key)
        try:
            daytona.delete(_sandbox)
        except Exception as e:
            print(f"Warning: Failed to delete sandbox: {e}")
    _sandbox = None
    _sandbox_ready = False


def ensure_sandbox_deps(api_key: Optional[str] = None) -> None:
    """
    Installs dependencies inside the sandbox the first time.
    This can take a bit, so do it BEFORE recording your demo.
    """
    global _sandbox_ready
    if _sandbox_ready:
        return

    sb = get_or_create_sandbox(api_key)

    # Install python deps in sandbox
    print("Installing sandbox dependencies (this may take a minute)...")
    sb.process.exec("python -V")
    sb.process.exec("pip install --upgrade pip")

    # Keep it minimal but sufficient
    sb.process.exec(
        "pip install easyocr==1.7.1 opencv-python-headless==4.9.0.80 "
        "pillow==10.2.0 numpy==1.26.4 pandas==2.2.0 requests==2.31.0"
    )

    _sandbox_ready = True
    print("Sandbox dependencies installed!")


def run_in_daytona(
    image_bytes: bytes,
    ocr_lang: str,
    target_lang: str,
    translator_backend: str,
    openai_key: str = "",
    openai_model: str = "gpt-4o-mini",
    daytona_api_key: Optional[str] = None,
    min_conf: float = 0.35,
    merge_lines: bool = True
) -> Dict[str, bytes]:
    """
    Uploads image + worker script to sandbox, runs processing, downloads results.
    Returns dict: {"annotated_png": bytes, "results_json": bytes, "results_csv": bytes}
    """
    sb = get_or_create_sandbox(daytona_api_key)
    ensure_sandbox_deps(daytona_api_key)

    # Upload inputs
    sb.fs.upload_file(image_bytes, "input.png")

    # Upload worker code (this file must exist locally in your repo)
    with open("sandbox_worker.py", "rb") as f:
        sb.fs.upload_file(f.read(), "sandbox_worker.py")

    # Build command
    cmd = (
        "python sandbox_worker.py "
        f"--image input.png "
        f"--ocr_lang {ocr_lang} "
        f"--target_lang {target_lang} "
        f"--backend '{translator_backend}' "
        f"--min_conf {min_conf} "
    )
    
    if merge_lines:
        cmd += "--merge_lines "
    
    if openai_key:
        cmd += f"--openai_key '{openai_key}' "
    
    cmd += f"--openai_model '{openai_model}'"

    # Run
    print(f"Running in sandbox: {cmd}")
    sb.process.exec(cmd)

    # Download outputs
    annotated_png = sb.fs.download_file("annotated.png")
    results_json = sb.fs.download_file("results.json")
    results_csv = sb.fs.download_file("results.csv")

    return {
        "annotated_png": annotated_png,
        "results_json": results_json,
        "results_csv": results_csv,
    }
