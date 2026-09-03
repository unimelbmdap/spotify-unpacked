#!/bin/sh
# Download the pinned, checksum-verified fonts into assets/fonts (or $1).
# Used by the Dockerfile at image build and by developers for local runs.
set -eu

DEST="${1:-$(dirname "$0")/../assets/fonts}"
mkdir -p "$DEST"

LITERATA_BASE="https://github.com/googlefonts/literata/raw/main/fonts/ttf"
POPPINS_BASE="https://github.com/google/fonts/raw/main/ofl/poppins"
NOTO_CJK="https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
NOTO_EMOJI="https://github.com/google/fonts/raw/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf"

fetch() {
  # fetch <url> <filename> <sha256>
  target="$DEST/$2"
  if [ -f "$target" ] && echo "$3  $target" | sha256sum -c --status - 2>/dev/null; then
    echo "ok       $2"
    return
  fi
  curl -fsSL --retry 3 -o "$target.part" "$1"
  echo "$3  $target.part" | sha256sum -c --status - || {
    echo "checksum mismatch for $2" >&2; rm -f "$target.part"; exit 1; }
  mv "$target.part" "$target"
  echo "fetched  $2"
}

fetch "$LITERATA_BASE/Literata-Regular.ttf"  Literata-Regular.ttf  0390890de9bb9d5862a6ba4125b82c61792ccc3d66b63e73eee75c1a16fcd208
fetch "$LITERATA_BASE/Literata-Italic.ttf"   Literata-Italic.ttf   198f70cc9a17bab578553fa274b81984d58c440efe26bc06f1d841c194b6691a
fetch "$LITERATA_BASE/Literata-Medium.ttf"   Literata-Medium.ttf   db2e5dab8536814ac5cf7e7f847778ec305010c2a7d681c219102803c49e6862
fetch "$LITERATA_BASE/Literata-SemiBold.ttf" Literata-SemiBold.ttf ee8f9413ebc974e1c1cfc76f6bdb9d08ddaadc66eeddd7320a65f8c581284d6d
fetch "$LITERATA_BASE/Literata-Bold.ttf"     Literata-Bold.ttf     b6af95b3b443cdbce964aa06741596987f2f5c3ede46a2bc846e5addd99d061f
fetch "$POPPINS_BASE/Poppins-Regular.ttf"  Poppins-Regular.ttf  7e65201e9b79159e2300267cc885e16c8dcef2424cdfa09a29bfb0980a94a7ba
fetch "$POPPINS_BASE/Poppins-Medium.ttf"   Poppins-Medium.ttf   90373e7d838d32468438fc3e152dca0bdb12edcab99ea639f158790b1ba1fd05
fetch "$POPPINS_BASE/Poppins-SemiBold.ttf" Poppins-SemiBold.ttf d3bf1bdaf0550e83da9ac0b1d1d9fe6db086835a83aa28578e609a394b9a0286
fetch "$POPPINS_BASE/Poppins-Bold.ttf"     Poppins-Bold.ttf     983676516167748b74de6f4771fb384c664fd913acb8b471122ecacf5da5ea6c
fetch "$NOTO_CJK"   NotoSansCJKjp-Regular.otf 68a3fc98800b2a27b371f2fb79991daf3633bd89309d4ffaa6946fd587f375b5
fetch "$NOTO_EMOJI" NotoEmoji-Regular.ttf     de6c18832938afc99caf132b39d6a30a19bac7f2e812e28db2535b4608d27551
