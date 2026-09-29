# Linux smoke test

Plays one battle of the real game on Linux inside Docker. It uses a virtual
1920x1080 display (Xvfb) with the Openbox window manager and DejaVu fonts only,
and drives it with real X keyboard and mouse events (xdotool). The script prints
a pass/fail line for each check and saves screenshots to `out/`.

From the repository root:

```bash
docker build -f tools/linux_smoke/Dockerfile -t artwar-linux .
docker run --rm -v "$PWD:/app" -v "$PWD/tools/linux_smoke/out:/out" artwar-linux run-on-xvfb tools/linux_smoke/smoke_linux.py /out
```
