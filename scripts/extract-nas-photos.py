#!/usr/bin/env python3
"""Extract GPS from NAS DCIM directories for a trip, via batch SSH."""
import argparse, json, os, subprocess, sys
from datetime import datetime

TRIPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trips")
SSH_SOCKET = os.path.expanduser("~/.ssh/nas.control")
SSH_HOST = "alienchang@192.168.1.100"
SSH_CMD = ["ssh", "-S", SSH_SOCKET, SSH_HOST]

# Use %% to escape % so the resulting NAS script has single %
NAS_SCRIPT = r"""import subprocess, json, os, re, sys
from datetime import datetime
DCIM = %s
START = datetime(%d,%d,%d)
END = datetime(%d,%d,%d,23,59,59)
def dms2dec(s):
    m = re.search(r"([\d.]+)deg\s+([\d.]+)'\s+([\d.]+)", s)
    if not m: return None
    return float(m.group(1)) + float(m.group(2))/60 + float(m.group(3))/3600
results = []
for base in DCIM:
    for root, dirs, files in os.walk(base):
        if "/@eaDir" in root: continue
        for f in sorted(files):
            if not f.upper().endswith((".JPG",".JPEG")): continue
            fp = os.path.join(root, f)
            try:
                r = subprocess.run(["exiv2","-pa","-g","GPS","-g","DateTimeOriginal",fp],
                    capture_output=True, text=True, timeout=10)
            except: continue
            dt_s = lat = lon = latref = lonref = alt = altref = None
            for line in r.stdout.split(chr(10)):
                if "DateTimeOriginal" in line and "Ascii" in line:
                    p = line.split()
                    if len(p) >= 5: dt_s = p[-2] + " " + p[-1]
                if "GPSLatitude" in line and "Rational" in line and "Ref" not in line:
                    lat = line.split("Rational",1)[-1].strip()
                if "GPSLongitude" in line and "Rational" in line and "Ref" not in line:
                    lon = line.split("Rational",1)[-1].strip()
                if "GPSLatitudeRef" in line: latref = line.split()[-1]
                if "GPSLongitudeRef" in line: lonref = line.split()[-1]
                if "GPSAltitude" in line and "Rational" in line and "Ref" not in line:
                    parts = line.split()
                    if parts: alt = parts[-1]
                if "GPSAltitudeRef" in line: altref = line.split()[-1]
            if dt_s and lat and lon:
                try: dt = datetime.strptime(dt_s, "%%Y:%%m:%%d %%H:%%M:%%S")
                except: continue
                if START <= dt <= END:
                    dl = dms2dec(lat)
                    dn = dms2dec(lon)
                    if dl and dn:
                        if latref == "South": dl = -dl
                        if lonref == "West": dn = -dn
                        alt_v = None
                        if alt:
                            try: alt_v = float(alt.replace("m","").strip())
                            except: pass
                            if altref == "1" and alt_v is not None: alt_v = -alt_v
                        results.append({"time":dt.isoformat(),"lat":round(dl,6),"lon":round(dn,6),"altitude":alt_v,"file":fp,"source":os.path.basename(base)})
    print(f"Scanned {base}: {len(results)}", file=sys.stderr)
print(json.dumps(results, ensure_ascii=False))
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trip", required=True)
    args = parser.parse_args()
    trip_path = os.path.join(TRIPS_DIR, f"{args.trip}.json")
    with open(trip_path) as f:
        trip = json.load(f)
    start = datetime.strptime(trip["dateStart"], "%Y-%m-%d")
    end = datetime.strptime(trip["dateEnd"], "%Y-%m-%d")
    dirs = json.dumps([
        "/volume1/photo/Other_Picture/iphone6s_alien/DCIM/112APPLE",
        "/volume1/photo/Other_Picture/iphone6s_alien/DCIM/113APPLE",
        "/volume1/photo/Other_Picture/iphone6s_alien/DCIM/114APPLE",
    ])
    script = NAS_SCRIPT % (dirs, start.year, start.month, start.day, end.year, end.month, end.day)
    proc = subprocess.Popen(SSH_CMD + ["python3"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(input=script, timeout=600)
    if stderr and stderr.strip():
        for line in stderr.strip().split("\n"):
            if line.strip(): print(line, file=sys.stderr)
    try: photos = json.loads(stdout.strip())
    except json.JSONDecodeError:
        print(f"Parse error. stdout: {stdout[:500]}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(photos, ensure_ascii=False))

if __name__ == "__main__":
    main()
