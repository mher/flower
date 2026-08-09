set -euxo pipefail

BOOTSTRAP_VERSION="${1:-5.3.8}"
BOOTSTRAP_ARCHIVE="v${BOOTSTRAP_VERSION}.zip"
BOOTSTRAP_BUILD_DIR=".build"
BOOTSTRAP_ZIP="${BOOTSTRAP_BUILD_DIR}/${BOOTSTRAP_ARCHIVE}"
BOOTSTRAP_DIR="${BOOTSTRAP_BUILD_DIR}/bootstrap-${BOOTSTRAP_VERSION}"

cd "$(git rev-parse --show-toplevel)"
mkdir -p "$BOOTSTRAP_BUILD_DIR"

if [ -f "$BOOTSTRAP_ZIP" ]; then
  rm "$BOOTSTRAP_ZIP"
fi

if [ ! -d "$BOOTSTRAP_DIR" ]; then
  curl --location --fail --output "$BOOTSTRAP_ZIP" \
    "https://github.com/twbs/bootstrap/archive/refs/tags/${BOOTSTRAP_ARCHIVE}"
  unzip "$BOOTSTRAP_ZIP" -d "$BOOTSTRAP_BUILD_DIR"
  rm "$BOOTSTRAP_ZIP"
fi

cp ./scss/flower.scss "$BOOTSTRAP_DIR/scss/flower.scss"
(
  cd "$BOOTSTRAP_DIR"
  npm install
  npx --no-install sass scss/flower.scss dist/css/bootstrap.min.css --style=compressed
  npm run js
)

cp "$BOOTSTRAP_DIR/dist/css/bootstrap.min.css" ./flower/static/css/
cp "$BOOTSTRAP_DIR/dist/css/bootstrap.min.css.map" ./flower/static/css/
cp "$BOOTSTRAP_DIR/dist/js/bootstrap.bundle.min.js" ./flower/static/js/
cp "$BOOTSTRAP_DIR/dist/js/bootstrap.bundle.min.js.map" ./flower/static/js/
