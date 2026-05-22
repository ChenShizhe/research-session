#!/usr/bin/env python3
"""Assemble an Excalidraw clipboard payload from a component manifest.

Reads a manifest JSON describing the figure's components (image elements plus
native shapes/text) and emits the `excalidraw/clipboard` JSON that Excalidraw
accepts on paste. Image files are embedded as base64 data-URLs in the `files` map;
each image's intrinsic size is read (SVG `viewBox`, or PNG IHDR) so aspect ratio is
preserved from a single target height.

Put the result on the clipboard and paste into Excalidraw:
    python assemble_payload.py manifest.json payload.json
    pbcopy < payload.json          # macOS; then Cmd+V on the canvas
Paste APPENDS to the current scene — it does not clear it.

Manifest schema (JSON):
{
  "elements": [
    {"kind":"image","id":"zLbl","path":"label-Z.svg","x":150,"y":120,"h":24},
    {"kind":"image","id":"yPanel","path":"panels/y.png","x":900,"y":120,"h":48,"w":200},
    {"kind":"rect","id":"zBox","x":70,"y":100,"w":180,"h":120,"stroke":"#4a9eed","dashed":false},
    {"kind":"line","id":"zL1","x":90,"y":160,"points":[[0,0],[140,0]],"stroke":"#4a9eed","width":3},
    {"kind":"arrow","id":"aZN","x":252,"y":150,"points":[[0,0],[86,0]],"stroke":"#1e1e1e","width":2.5,"dashed":false},
    {"kind":"text","id":"cap","x":150,"y":300,"text":"\\textbf{Caption.} ...","fontSize":13,"color":"#1e1e1e","fontFamily":3}
  ]
}
Image dims: give "h" (height); "w" is computed from the file's aspect ratio unless
provided. fontFamily: 1=hand-drawn, 2=normal, 3=code (good for editable LaTeX
source captions).
"""
import argparse, base64, json, os, re, struct, random, time

def _seed():
    return random.randint(1, 2_000_000_000)

def _img_dims(path: str, raw: bytes):
    if path.lower().endswith(".svg"):
        m = re.search(rb"viewBox=['\"]([-\d.eE]+) ([-\d.eE]+) ([\d.eE]+) ([\d.eE]+)['\"]", raw)
        if not m:
            raise ValueError(f"no viewBox in {path}")
        return float(m.group(3)), float(m.group(4)), "image/svg+xml"
    if path.lower().endswith(".png"):
        w, h = struct.unpack(">II", raw[16:24])  # PNG IHDR width/height
        return float(w), float(h), "image/png"
    if path.lower().endswith((".jpg", ".jpeg")):
        return 1.0, 1.0, "image/jpeg"  # aspect unknown; require explicit w/h
    raise ValueError(f"unsupported image type: {path}")

def build(manifest: dict, manifest_dir: str) -> dict:
    now = int(time.time() * 1000)
    elements, files = [], {}

    def base(o: dict):
        d = dict(angle=0, strokeColor="#1e1e1e", backgroundColor="transparent",
                 fillStyle="solid", strokeWidth=2, strokeStyle="solid", roughness=1,
                 opacity=100, groupIds=[], frameId=None, roundness=None, seed=_seed(),
                 version=1, versionNonce=_seed(), isDeleted=False, boundElements=None,
                 updated=now, link=None, locked=False)
        d.update(o)
        elements.append(d)

    def poly(e, kind, arrow):
        pts = e["points"]
        w = max(1, max(abs(p[0]) for p in pts))
        h = max(1, max(abs(p[1]) for p in pts))
        base(dict(type=kind, id=e["id"], x=e["x"], y=e["y"], width=w, height=h,
                  strokeColor=e.get("stroke", "#1e1e1e"), strokeWidth=e.get("width", 2),
                  strokeStyle="dashed" if e.get("dashed") else "solid", points=pts,
                  lastCommittedPoint=None, startBinding=None, endBinding=None,
                  startArrowhead=None, endArrowhead="arrow" if arrow else None))

    for e in manifest["elements"]:
        kind = e["kind"]
        if kind == "image":
            path = e["path"] if os.path.isabs(e["path"]) else os.path.join(manifest_dir, e["path"])
            with open(path, "rb") as f:
                raw = f.read()
            iw, ih, mime = _img_dims(path, raw)
            h = e["h"]
            w = e.get("w") or round(h * iw / ih, 2)
            fid = "file_" + e["id"]
            files[fid] = {"mimeType": mime, "id": fid,
                          "dataURL": f"data:{mime};base64," + base64.b64encode(raw).decode(),
                          "created": now, "lastRetrieved": now}
            base(dict(type="image", id=e["id"], x=e["x"], y=e["y"], width=w, height=h,
                      status="saved", fileId=fid, scale=[1, 1]))
        elif kind == "rect":
            base(dict(type="rectangle", id=e["id"], x=e["x"], y=e["y"], width=e["w"],
                      height=e["h"], strokeColor=e.get("stroke", "#1e1e1e"),
                      strokeWidth=e.get("width", 2), roundness={"type": 3},
                      strokeStyle="dashed" if e.get("dashed") else "solid"))
        elif kind == "line":
            poly(e, "line", False)
        elif kind == "arrow":
            poly(e, "arrow", True)
        elif kind == "text":
            t = e["text"]
            lines = t.split("\n")
            fs = e.get("fontSize", 16)
            base(dict(type="text", id=e["id"], x=e["x"], y=e["y"],
                      width=max(len(s) for s in lines) * fs * 0.55, height=len(lines) * fs * 1.3,
                      strokeColor=e.get("color", "#1e1e1e"), text=t, fontSize=fs,
                      fontFamily=e.get("fontFamily", 1), textAlign="left", verticalAlign="top",
                      containerId=None, originalText=t, autoResize=True, lineHeight=1.25))
        else:
            raise ValueError(f"unknown element kind: {kind}")

    return {"type": "excalidraw/clipboard", "elements": elements, "files": files}

def main():
    ap = argparse.ArgumentParser(description="Assemble an Excalidraw clipboard payload from a manifest.")
    ap.add_argument("manifest", help="manifest JSON path")
    ap.add_argument("out", help="output payload JSON path")
    a = ap.parse_args()
    manifest = json.load(open(a.manifest))
    payload = build(manifest, os.path.dirname(os.path.abspath(a.manifest)))
    with open(a.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"elements={len(payload['elements'])} images={len(payload['files'])} "
          f"bytes={os.path.getsize(a.out)} -> {a.out}")

if __name__ == "__main__":
    main()
