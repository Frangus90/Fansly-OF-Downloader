"""Manages the embedded Python environment for OCR operations.

Handles downloading an embeddable Python, installing easyocr into it,
and running the persistent OCR worker subprocess.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import traceback
import zipfile
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen, Request


def _get_log_path() -> Path:
    """Return path for the OCR debug log file."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "ocr_debug.log"
    return Path.cwd() / "ocr_debug.log"


_ocr_logger = logging.getLogger("ocr_env")
_ocr_logger.setLevel(logging.DEBUG)
_handler = logging.FileHandler(_get_log_path(), encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_ocr_logger.addHandler(_handler)


PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_ZIP = f"python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{PYTHON_EMBED_ZIP}"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# Available PyTorch CUDA wheel indexes, ordered newest to oldest.
# Each entry is (cuda_major, cuda_minor, index_url).
# The installer picks the highest version that doesn't exceed the driver's CUDA version.
_TORCH_CUDA_WHEELS = [
    (12, 8, "https://download.pytorch.org/whl/cu128"),
    (12, 6, "https://download.pytorch.org/whl/cu126"),
    (12, 4, "https://download.pytorch.org/whl/cu124"),
    (12, 1, "https://download.pytorch.org/whl/cu121"),
    (11, 8, "https://download.pytorch.org/whl/cu118"),
]

ProgressCallback = Optional[Callable[[str, float], None]]


def detect_cuda() -> Optional[str]:
    """Detect NVIDIA GPU CUDA version via nvidia-smi.

    Returns the CUDA version string (e.g. "12.8") or None if no NVIDIA GPU.
    """
    try:
        import shutil
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            _ocr_logger.info("CUDA detection: nvidia-smi not found")
            return None

        result = subprocess.run(
            [nvidia_smi],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            _ocr_logger.info(f"CUDA detection: nvidia-smi failed: {result.stderr.strip()}")
            return None

        import re
        match = re.search(r"CUDA Version:\s*(\d+\.\d+)", result.stdout)
        if match:
            cuda_ver = match.group(1)
            _ocr_logger.info(f"CUDA detection: found CUDA {cuda_ver}")
            return cuda_ver

        _ocr_logger.info("CUDA detection: could not parse CUDA version from nvidia-smi")
        return None
    except Exception as e:
        _ocr_logger.info(f"CUDA detection: exception: {e}")
        return None


def get_torch_index_url(cuda_version: Optional[str]) -> Optional[str]:
    """Pick the best PyTorch CUDA wheel index for the detected driver CUDA version.

    Selects the highest available wheel version that does not exceed
    the driver's CUDA version (wheels are backwards compatible within
    a major version, but cannot exceed the driver's CUDA).
    """
    if not cuda_version:
        return None

    try:
        parts = cuda_version.split(".")
        driver_major = int(parts[0])
        driver_minor = int(parts[1])
    except (IndexError, ValueError):
        _ocr_logger.info(f"CUDA {cuda_version} -> could not parse, using CPU")
        return None

    for wheel_major, wheel_minor, url in _TORCH_CUDA_WHEELS:
        if (wheel_major, wheel_minor) <= (driver_major, driver_minor):
            _ocr_logger.info(
                f"CUDA {cuda_version} -> torch index: cu{wheel_major}{wheel_minor} ({url})"
            )
            return url

    _ocr_logger.info(f"CUDA {cuda_version} -> no compatible torch wheel, using CPU")
    return None


def get_ocr_env_dir() -> Path:
    """Return the ocr_env directory path (next to exe when frozen, cwd otherwise)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "ocr_env"
    return Path.cwd() / "ocr_env"


def get_worker_script() -> Path:
    """Return path to ocr_worker.py."""
    if getattr(sys, "frozen", False):
        # PyInstaller --add-data places files in sys._MEIPASS (_internal/)
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "ocr_worker.py"
    return Path(__file__).resolve().parent.parent / "ocr_worker.py"


def is_ocr_installed() -> bool:
    """Check if the embedded OCR environment is ready to use."""
    if not getattr(sys, "frozen", False):
        try:
            import easyocr  # noqa: F401
            _ocr_logger.debug("is_ocr_installed: True (direct import)")
            return True
        except ImportError:
            pass

    env_dir = get_ocr_env_dir()
    python_exe = env_dir / "python.exe"
    if not python_exe.exists():
        _ocr_logger.debug(f"is_ocr_installed: False (no python.exe at {python_exe})")
        return False

    easyocr_pkg = env_dir / "Lib" / "site-packages" / "easyocr"
    result = easyocr_pkg.is_dir()
    _ocr_logger.debug(f"is_ocr_installed: {result} (easyocr_pkg={easyocr_pkg})")
    return result


def _download_file(url: str, dest: Path, label: str, callback: ProgressCallback = None):
    """Download a file with progress reporting."""
    req = Request(url, headers={"User-Agent": "FanslyDLNG"})
    response = urlopen(req, timeout=60)
    total = int(response.headers.get("Content-Length", 0))
    downloaded = 0
    chunk_size = 64 * 1024

    with open(dest, "wb") as f:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if callback and total > 0:
                mb_done = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                callback(f"{label}... {mb_done:.1f}/{mb_total:.1f} MB", downloaded / total)


def _enable_site_packages(env_dir: Path):
    """Modify the ._pth file to enable site-packages (uncomment 'import site')."""
    for pth_file in env_dir.glob("python*._pth"):
        lines = pth_file.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            if line.strip() == "#import site":
                new_lines.append("import site")
            else:
                new_lines.append(line)
        pth_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return
    raise FileNotFoundError("No python*._pth file found in embedded Python")


def install_ocr_env(callback: ProgressCallback = None):
    """Download embedded Python and install easyocr into it.

    Args:
        callback: Called with (message: str, progress: float 0.0-1.0 or -1 for indeterminate)
    """
    env_dir = get_ocr_env_dir()
    env_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Download embedded Python
    zip_path = env_dir.parent / PYTHON_EMBED_ZIP
    try:
        if callback:
            callback("Downloading Python runtime...", 0.0)
        _download_file(PYTHON_EMBED_URL, zip_path, "Downloading Python runtime", callback)

        # Step 2: Extract
        if callback:
            callback("Extracting Python runtime...", -1)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(env_dir)

        # Step 3: Enable site-packages
        _enable_site_packages(env_dir)

        # Step 4: Download get-pip.py
        get_pip_path = env_dir / "get-pip.py"
        if callback:
            callback("Downloading pip...", -1)
        _download_file(GET_PIP_URL, get_pip_path, "Downloading pip", callback)

        # Step 5: Install pip
        python_exe = str(env_dir / "python.exe")
        if callback:
            callback("Installing pip...", -1)
        subprocess.run(
            [python_exe, str(get_pip_path)],
            capture_output=True, timeout=120, check=True,
        )
        get_pip_path.unlink(missing_ok=True)

        # Step 6: Detect GPU and install PyTorch
        cuda_version = detect_cuda()
        torch_index = get_torch_index_url(cuda_version)

        if torch_index:
            if callback:
                callback(f"Installing PyTorch with CUDA {cuda_version} (this downloads ~2.5 GB)...", -1)
            _ocr_logger.info(f"Installing torch with CUDA from {torch_index}")
            torch_result = subprocess.run(
                [python_exe, "-m", "pip", "install", "torch", "torchvision",
                 "--index-url", torch_index],
                capture_output=True, text=True, timeout=1800,
            )
            if torch_result.returncode != 0:
                _ocr_logger.warning(f"CUDA torch install failed, falling back to CPU: {torch_result.stderr[:500]}")
                if callback:
                    callback("CUDA install failed, falling back to CPU...", -1)
                # Fall through to easyocr install which will pull CPU torch

        # Step 7: Install easyocr
        if callback:
            if torch_index:
                callback("Installing EasyOCR...", -1)
            else:
                callback("Installing EasyOCR (this downloads ~1.5 GB)...", -1)
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "easyocr"],
            capture_output=True, text=True, timeout=1800,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pip install easyocr failed:\n{result.stderr}")

        # Step 8: Verify
        if callback:
            callback("Verifying installation...", -1)
        verify = subprocess.run(
            [python_exe, "-c",
             "import easyocr; import torch; "
             "gpu = torch.cuda.is_available(); "
             "print(f'ok gpu={gpu}')"],
            capture_output=True, text=True, timeout=30,
        )
        if verify.returncode != 0 or "ok" not in verify.stdout:
            raise RuntimeError(f"Verification failed:\n{verify.stderr}")

        gpu_enabled = "gpu=True" in verify.stdout
        _ocr_logger.info(f"Verification passed. GPU enabled: {gpu_enabled}")

        if callback:
            status = "EasyOCR: Ready (GPU)" if gpu_enabled else "EasyOCR: Ready (CPU)"
            callback(status, 1.0)

    finally:
        zip_path.unlink(missing_ok=True)


def uninstall_ocr_env():
    """Remove the embedded OCR environment."""
    import shutil
    env_dir = get_ocr_env_dir()
    if env_dir.is_dir():
        shutil.rmtree(env_dir)


class OcrProcess:
    """Manages a persistent OCR worker subprocess.

    The worker process is started on first use and kept alive for
    subsequent calls. If the process dies, it is restarted automatically.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def _get_python_exe(self) -> str:
        """Get the Python executable to use for the worker."""
        if not getattr(sys, "frozen", False):
            return sys.executable
        return str(get_ocr_env_dir() / "python.exe")

    def _ensure_running(self):
        """Start the worker process if it's not running."""
        if self._process is not None and self._process.poll() is None:
            return

        python_exe = self._get_python_exe()
        worker_script = str(get_worker_script())

        _ocr_logger.info(f"Starting OCR worker: {python_exe} {worker_script}")
        _ocr_logger.info(f"Python exe exists: {os.path.exists(python_exe)}")
        _ocr_logger.info(f"Worker script exists: {os.path.exists(worker_script)}")

        self._process = subprocess.Popen(
            [python_exe, worker_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        _ocr_logger.info(f"Worker process started, pid={self._process.pid}")

    def _send_request(self, request: dict, timeout: float = 300) -> dict:
        """Send a JSON request and read the JSON response."""
        with self._lock:
            self._ensure_running()

            line = json.dumps(request) + "\n"
            _ocr_logger.debug(f"Sending request: {request.get('cmd', '?')}")
            try:
                self._process.stdin.write(line)
                self._process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                _ocr_logger.warning(f"Pipe error, restarting worker: {e}")
                self._process = None
                self._ensure_running()
                self._process.stdin.write(line)
                self._process.stdin.flush()

            response_line = self._process.stdout.readline()
            if not response_line:
                stderr = ""
                if self._process.stderr:
                    stderr = self._process.stderr.read()
                _ocr_logger.error(f"Worker died. stderr:\n{stderr}")
                self._process = None
                raise RuntimeError(f"OCR worker process died unexpectedly.\nstderr: {stderr}")

            _ocr_logger.debug(f"Response received: {response_line[:200]}")
            return json.loads(response_line)

    def detect_text(
        self,
        image_path: str,
        text_threshold: float = 0.7,
        low_text: float = 0.4,
        mag_ratio: float = 1.0,
    ) -> list[dict]:
        """Run OCR on an image via the worker subprocess.

        Returns list of dicts with keys: 'bbox' (tuple), 'text', 'confidence'.
        bbox is (y_min, y_max, x_min, x_max) in pixel coordinates.
        """
        response = self._send_request({
            "cmd": "detect",
            "image_path": str(image_path),
            "text_threshold": text_threshold,
            "low_text": low_text,
            "mag_ratio": mag_ratio,
        })

        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "OCR detection failed"))

        for det in response["detections"]:
            det["bbox"] = tuple(det["bbox"])

        return response["detections"]

    def stop(self):
        """Shut down the worker process."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                try:
                    self._process.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                    self._process.stdin.flush()
                    self._process.wait(timeout=5)
                except Exception:
                    self._process.kill()
                self._process = None
